#!/usr/bin/env python

# Copyright 2023 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Validate consistency of adapter / port / NIC metrics for CPCs in DPM mode
"""

import sys
import argparse
import getpass

import requests
import zhmcclient


def parse_args():
    """
    Parse the command line arguments.
    """

    parser = argparse.ArgumentParser(
        add_help=False,
        description="Validate consistency of adapter / port / NIC metrics for "
        "CPCs in DPM mode")

    parser.add_argument("--help", action='help', default=argparse.SUPPRESS,
                        help="Show this help message and exit")

    parser.add_argument("-h", dest='host', metavar='HOST', action='store',
                        help="HMC host")

    parser.add_argument("-u", dest='userid', metavar='USERID', action='store',
                        help="HMC userid (password is prompted)")

    parser.add_argument("-n", dest='no_verify', action='store_true',
                        help="Do not verify HMC server certificate")

    return parser.parse_args()


def main():
    "Main function"
    requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member

    args = parse_args()

    password = getpass.getpass(
        prompt=f"Password for user {args.userid} on HMC {args.host}: ")
    session = zhmcclient.Session(
        host=args.host, userid=args.userid, password=password,
        verify_cert=not args.no_verify)
    client = zhmcclient.Client(session)

    # Adapter status values for which we expect adapter & port metrics
    expected_adapter_statuses = (
        "active",
        "exceptions",
        "service",
    )

    network_adapter_types = (
        "hipersockets",
        "osd",
        "osm",
        "osc",
        "ose",
        "roce",
        "roc2",
        "cna",
    )

    # Partition status values for which we expect NIC metrics
    expected_partition_statuses = (
        "terminated",
        "active",
        "reservation-error",
        "paused",
    )

    # Determine the resources for which we expect metrics

    print("Listing CPCs...")
    cpcs = client.cpcs.list()

    print("Listing adapters...")
    all_adapters = {}
    expected_adapters = {}
    expected_network_adapters = {}
    for cpc in cpcs:
        adapters = cpc.adapters.list()
        for a in adapters:
            all_adapters[a.uri] = a
            if a.get_property('status') in expected_adapter_statuses:
                expected_adapters[a.uri] = a
                if a.get_property('type') in network_adapter_types:
                    expected_network_adapters[a.uri] = a

    print("Listing partitions...")
    all_partitions = {}
    expected_partitions = {}
    for cpc in cpcs:
        partitions = cpc.partitions.list()
        for p in partitions:
            all_partitions[p.uri] = p
            if p.get_property('status') in expected_partition_statuses:
                expected_partitions[p.uri] = p

    print("Listing partition NICs...")
    all_nics = {}
    expected_nics = {}
    for p in all_partitions.values():
        nics = p.nics.list()
        for n in nics:
            all_nics[n.uri] = n
            if p.get_property('status') in expected_partition_statuses:
                expected_nics[n.uri] = n

    # Create the metric context for retrieving metric values
    metric_groups = [
        'adapter-usage',
        'network-physical-adapter-port',
        'partition-attached-network-interface',
    ]
    mc = client.metrics_contexts.create(
        {'anticipated-frequency-seconds': 15,
         'metric-groups': metric_groups})

    # Retrieve the metric values and determine corresponding resource URIs
    print("Retrieving metrics...")
    actual_nic_uris = set()
    actual_port_adapter_uris = set()
    actual_adapter_uris = set()
    mr_str = mc.get_metrics()
    mr = zhmcclient.MetricsResponse(mc, mr_str)
    for mg in mr.metric_group_values:
        for ov in mg.object_values:
            if mg.name == 'adapter-usage':
                actual_adapter_uris.add(ov.resource_uri)
            elif mg.name == 'network-physical-adapter-port':
                actual_port_adapter_uris.add(ov.resource_uri)
            elif mg.name == 'partition-attached-network-interface':
                actual_nic_uris.add(ov.resource_uri)

    # Get the resource objects for the resource URIs
    actual_usage_adapters = {}
    for uri in actual_adapter_uris:
        adapter = all_adapters[uri]
        actual_usage_adapters[uri] = adapter
    actual_port_adapters = {}
    for uri in actual_port_adapter_uris:
        adapter = all_adapters[uri]
        actual_port_adapters[uri] = adapter
    actual_nics = {}
    for uri in actual_nic_uris:
        nic = all_nics[uri]
        actual_nics[uri] = nic

    # Determine missing/unexpected adapters for adapter-usage metrics
    missing_usage_adapters = []
    for adapter in expected_adapters.values():
        if adapter.uri not in actual_usage_adapters:
            missing_usage_adapters.append(adapter)
    unexpected_usage_adapters = []
    for uri in actual_usage_adapters:
        if uri not in expected_adapters:
            adapter = all_adapters[uri]
            unexpected_usage_adapters.append(adapter)

    print("\nIssues with metrics:")

    print("  Adapters with missing adapter-usage metrics (CPC / adapter):")
    for adapter in sorted(missing_usage_adapters,
                          key=lambda x: (x.manager.parent.name, x.name)):
        cpc = adapter.manager.parent
        print("    {} / {} (type: {}, status: {})".
              format(cpc.name, adapter.name,
                     adapter.get_property('type'),
                     adapter.get_property('status')))

    print("  Adapters with unexpected adapter-usage metrics (CPC / adapter):")
    for adapter in sorted(unexpected_usage_adapters,
                          key=lambda x: (x.manager.parent.name, x.name)):
        cpc = adapter.manager.parent
        print("    {} / {} (type: {}, status: {})".
              format(cpc.name, adapter.name,
                     adapter.get_property('type'),
                     adapter.get_property('status')))

    # Determine missing/unexpected adapters
    #   for network-physical-adapter-port metrics
    missing_port_adapters = []
    for adapter in expected_network_adapters.values():
        if adapter.uri not in actual_port_adapters:
            missing_port_adapters.append(adapter)
    unexpected_port_adapters = []
    for uri in actual_port_adapters:
        if uri not in expected_network_adapters:
            adapter = all_adapters[uri]
            unexpected_port_adapters.append(adapter)

    print("  Adapters with missing network-physical-adapter-port metrics "
          "(CPC / adapter):")
    for adapter in sorted(missing_port_adapters,
                          key=lambda x: (x.manager.parent.name, x.name)):
        cpc = adapter.manager.parent
        print("    {} / {} (type: {}, status: {})".
              format(cpc.name, adapter.name,
                     adapter.get_property('type'),
                     adapter.get_property('status')))

    print("  Adapters with unexpected network-physical-adapter-port metrics "
          "(CPC / adapter):")
    for adapter in sorted(unexpected_port_adapters,
                          key=lambda x: (x.manager.parent.name, x.name)):
        cpc = adapter.manager.parent
        print("    {} / {} (type: {}, status: {})".
              format(cpc.name, adapter.name,
                     adapter.get_property('type'),
                     adapter.get_property('status')))

    # Determine missing/unexpected nics for
    #   partition-attached-network-interface metrics
    missing_nics = []
    for nic in expected_nics.values():
        if nic.uri not in actual_nics:
            missing_nics.append(nic)
    unexpected_nics = []
    for uri in actual_nics:
        if uri not in expected_nics:
            nic = all_nics[uri]
            unexpected_nics.append(nic)

    print("  NICs with missing partition-attached-network-interface metrics "
          "(CPC / partition / NIC):")
    for nic in sorted(missing_nics,
                      key=lambda x: (x.manager.parent.manager.parent.name,
                                     x.manager.parent.name, x.name)):
        partition = nic.manager.parent
        cpc = partition.manager.parent
        print("    {} / {} / {} (part.status: {})".
              format(cpc.name, partition.name, nic.name,
                     partition.get_property('status')))

    print("  NICs with unexpected partition-attached-network-interface metrics "
          "(CPC / partition / NIC):")
    for nic in sorted(unexpected_nics,
                      key=lambda x: (x.manager.parent.manager.parent.name,
                                     x.manager.parent.name, x.name)):
        partition = nic.manager.parent
        cpc = partition.manager.parent
        print("    {} / {} / {} (part.status: {})".
              format(cpc.name, partition.name, nic.name,
                     partition.get_property('status')))

    print("\nActual metrics:")

    print("  Adapters with adapter-usage metrics (CPC / adapter):")
    for adapter in sorted(actual_usage_adapters.values(),
                          key=lambda x: (x.manager.parent.name, x.name)):
        cpc = adapter.manager.parent
        print("    {} / {} (type: {}, status: {})".
              format(cpc.name, adapter.name,
                     adapter.get_property('type'),
                     adapter.get_property('status')))

    print("  Adapters with network-physical-adapter-port metrics "
          "(CPC / adapter):")
    for adapter in sorted(actual_port_adapters.values(),
                          key=lambda x: (x.manager.parent.name, x.name)):
        cpc = adapter.manager.parent
        print("    {} / {} (type: {}, status: {})".
              format(cpc.name, adapter.name,
                     adapter.get_property('type'),
                     adapter.get_property('status')))

    print("  NICs with partition-attached-network-interface metrics "
          "(CPC / partition / NIC):")
    for nic in sorted(actual_nics.values(),
                      key=lambda x: (x.manager.parent.manager.parent.name,
                                     x.manager.parent.name, x.name)):
        partition = nic.manager.parent
        cpc = partition.manager.parent
        print("    {} / {} / {} (part.status: {})".
              format(cpc.name, partition.name, nic.name,
                     partition.get_property('status')))

    # Cleanup
    mc.delete()
    session.logoff()


if __name__ == "__main__":
    try:
        main()
    except zhmcclient.Error as exc:
        print(f"Error: {exc}")
        sys.exit(1)
