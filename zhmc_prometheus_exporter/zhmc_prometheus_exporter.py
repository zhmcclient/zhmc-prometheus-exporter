#!/usr/bin/env python

# Copyright 2018 IBM Corp. All Rights Reserved.
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
A prometheus.io exporter for metrics from the Z Hardware Management Console
"""

import argparse
import sys
import time
import ipaddress
import warnings
import re
import urllib3

import yaml
import zhmcclient
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY

DEFAULT_CREDS_FILE = '/etc/zhmc-prometheus-exporter/hmccreds.yaml'
DEFAULT_METRICS_FILE = '/etc/zhmc-prometheus-exporter/metrics.yaml'


class YAMLInfoNotFoundError(Exception):
    """A custom error that is raised when something that was expected in a
    YAML cannot be found.
    """
    pass


class ConnectionError(Exception):
    # pylint: disable=redefined-builtin
    """Unwrapped from zhmcclient"""
    pass


class AuthError(Exception):
    """Unwrapped from zhmcclient"""
    pass


class OtherError(Exception):
    """Other exceptions raised by zhmcclient"""
    pass


class ProperExit(Exception):
    """Terminating while the server was running"""
    pass


class ImproperExit(Exception):
    """Terminating because something went wrong"""
    pass


def parse_args(args):
    """Parses the CLI arguments."""
    parser = argparse.ArgumentParser(description="Prometheus.io exporter for "
                                     "the IBM Z Hardware Management Console")
    parser.add_argument("-p", metavar="PORT",
                        default="9291",
                        help="port for exporting. Default: 9291")
    parser.add_argument("-c", metavar="CREDS_FILE",
                        default=DEFAULT_CREDS_FILE,
                        help="path name of HMC credentials file. "
                        "Use --help-creds for details. "
                        "Default: {}".format(DEFAULT_CREDS_FILE))
    parser.add_argument("-m", metavar="METRICS_FILE",
                        default=DEFAULT_METRICS_FILE,
                        help="path name of metric definition file. "
                        "Use --help-metrics for details. "
                        "Default: {}".format(DEFAULT_METRICS_FILE))
    parser.add_argument("--help-creds", action='store_true',
                        help="show help for HMC credentials file and exit")
    parser.add_argument("--help-metrics", action='store_true',
                        help="show help for metric definition file and exit")
    return parser.parse_args(args)


def help_creds():
    """
    Print help for HMC credentials file.
    """
    print("""
Help for HMC credentials file

The HMC credentials file is a YAML file that defines the IP address of the HMC
and the userid and password for logging on to the HMC.

The HMC userid must be authorized for object access permission to the resources
for which metrics are to be returned. Metrics of resources for which the userid
does not have object access permission will not be included in the result,
without raising an error.

The following example shows a complete HMC credentials file. For more details,
see the documentation at https://zhmc-prometheus-exporter.readthedocs.io/.

---
metrics:
  hmc: 1.2.3.4
  userid: myuser
  password: mypassword
""")


def help_metrics():
    """
    Print help for metric definition file.
    """
    print("""
Help for metric definition file

The metric definition file is a YAML file that defines which metrics are
exported to prometheus and under which names.

The following example shows a complete metric definition file that defines
a small subset of metrics and metric groups for DPM mode to be exported. For
more details and a full list of metrics and metric groups, see the
documentation at https://zhmc-prometheus-exporter.readthedocs.io/.

---
metric_groups:
  dpm-system-usage-overview:
    prefix: dpm
    fetch: True
  partition-usage:
    prefix: partition
    fetch: True
  # ...
metrics:
  dpm-system-usage-overview:
    network-usage:
      percent: True
      exporter_name: network_usage_ratio
      exporter_desc: DPM total network usage
    temperature-celsius:
      percent: False
      exporter_name: temperature_celsius
      exporter_desc: DPM temperature
    # ...
  partition-usage:
    accelerator-usage:
      percent: True
      exporter_name: accelerator_usage_ratio
      exporter_desc: Partition accelerator usage
    crypto-usage:
      percent: True
      exporter_name: crypto_usage_ratio
      exporter_desc: Partition crypto usage
    # ...
  # ...
""")


def parse_yaml_file(yamlfile, name):
    """Takes a YAML file name.
    Returns a parsed version of that file i.e. nests of dictionaries and lists.
    """
    try:
        with open(yamlfile, "r") as yamlcontent:
            return yaml.safe_load(yamlcontent)
    except PermissionError:
        raise PermissionError("Permission error reading {} {}".
                              format(name, yamlfile))
    except FileNotFoundError:
        raise FileNotFoundError("Cannot find {} {}".
                                format(name, yamlfile))


def parse_yaml_sections(yamlcontent, sought_sections, filename):
    """Takes nests of dictionaries and lists, the required sections,
    and the name of the YAML file for error output.
    Returns a list of the parsed sections as dictionaries.
    """
    parsed_sections = []
    for sought_section in sought_sections:
        section = yamlcontent.get(sought_section, None)
        if section is None:
            raise YAMLInfoNotFoundError("Section {} not found in file {}".
                                        format(sought_section, filename))
        parsed_sections.append(section)
    return parsed_sections


def check_creds_yaml(yaml_creds, filename):
    """Verify all required information in the credentials YAML file is given.
    Takes the dictionary retrieved from parse_yaml_sections and the name of
    the YAML file for error output.
    """
    if "hmc" not in yaml_creds:
        raise YAMLInfoNotFoundError("The 'hmc' property is missing in "
                                    "HMC credentials file {}".
                                    format(filename))
    try:
        ipaddress.ip_address(yaml_creds["hmc"])
    except ValueError:
        raise YAMLInfoNotFoundError("The 'hmc' property specifies an invalid "
                                    "IP address '{}' in HMC credentials file "
                                    "{}".
                                    format(yaml_creds["hmc"], filename))
    if "userid" not in yaml_creds:
        raise YAMLInfoNotFoundError("The 'userid' property is missing in "
                                    "HMC credentials file {}".
                                    format(filename))
    if "password" not in yaml_creds:
        raise YAMLInfoNotFoundError("The 'password' property is missing in "
                                    "HMC credentials file {}".
                                    format(filename))


def check_metrics_yaml(yaml_metric_groups, yaml_metrics, filename):
    """Verify all required information in the metrics YAML file is given.
    Takes the metric_groups dictionary from the metrics YAML file that
    specifies the known groups, the exporter prefix, and whether the metric
    group should actually be fetched, the metrics dictionary from the metrics
    YAML file that specifies the metrics per group, a percent boolean value,
    the name, and the description for the exporter, and the name of the YAML
    file for error output.
    """
    for metric_group in yaml_metric_groups:
        if "prefix" not in yaml_metric_groups[metric_group]:
            raise YAMLInfoNotFoundError("The 'prefix' property is missing in "
                                        "metric group '{}' in the "
                                        "'metric_groups' section in metric "
                                        "definition file {}".
                                        format(metric_group, filename))
        if "fetch" not in yaml_metric_groups[metric_group]:
            raise YAMLInfoNotFoundError("The 'fetch' property is missing in "
                                        "metric group '{}' in the "
                                        "'metric_groups' section in metric "
                                        "definition file {}".
                                        format(metric_group, filename))
        fetch = yaml_metric_groups[metric_group]["fetch"]
        if fetch not in (True, False):
            raise YAMLInfoNotFoundError("The 'fetch' property has an invalid "
                                        "boolean value '{}' in metric group "
                                        "'{}' in the 'metric_groups' section "
                                        "in metric definition file {}".
                                        format(fetch, metric_group, filename))
    for metric_group in yaml_metrics:
        if metric_group not in yaml_metric_groups:
            raise YAMLInfoNotFoundError("The metric group '{}' specified in "
                                        "the 'metrics' section is not defined "
                                        "in the 'metric_groups' section in "
                                        "metric definition file {}".
                                        format(metric_group, filename))
        for metric in yaml_metrics[metric_group]:
            if "percent" not in yaml_metrics[metric_group][metric]:
                raise YAMLInfoNotFoundError("The 'percent' property is "
                                            "missing in metric '{}' in metric "
                                            "group '{}' in the 'metrics' "
                                            "section in metric definition file "
                                            "{}".
                                            format(metric, metric_group,
                                                   filename))
            percent = yaml_metrics[metric_group][metric]["percent"]
            if percent not in (True, False):
                raise YAMLInfoNotFoundError("The 'percent' property has an "
                                            "invalid boolean value '{}' in "
                                            "metric '{}' in metric group '{}' "
                                            "in the 'metrics' section in "
                                            "metric definition file {}".
                                            format(fetch, metric, metric_group,
                                                   filename))
            if "exporter_name" not in yaml_metrics[metric_group][metric]:
                raise YAMLInfoNotFoundError("The 'exporter_name' property is "
                                            "missing in metric '{}' in metric "
                                            "group '{}' in the 'metrics' "
                                            "section in metric definition file "
                                            "{}".
                                            format(metric, metric_group,
                                                   filename))
            if "exporter_desc" not in yaml_metrics[metric_group][metric]:
                raise YAMLInfoNotFoundError("The 'exporter_desc' property is "
                                            "missing in metric '{}' in metric "
                                            "group '{}' in the 'metrics' "
                                            "section in metric definition file "
                                            "{}".
                                            format(metric, metric_group,
                                                   filename))


# Metrics context creation & deletion and retrieval derived from
# github.com/zhmcclient/python-zhmcclient/examples/metrics.py
def create_session(cred_dict):
    """To create a context, a session must be created first.
    Takes a dictionary with the HMC IP, the user ID, and a password.
    Returns the session.
    """
    # These warnings do not concern us
    urllib3.disable_warnings()
    session = zhmcclient.Session(cred_dict["hmc"],
                                 cred_dict["userid"],
                                 cred_dict["password"])
    return session


def create_metrics_context(session, yaml_metric_groups, filename):
    """Creating a context is mandatory for reading metrics from the Z HMC.
    Takes the session, the metric_groups dictionary from the metrics YAML file
    for fetch/do not fetch information, and the name of the YAML file for error
    output.
    Returns the context.
    """
    try:
        client = zhmcclient.Client(session)
        fetched_metric_groups = []
        for metric_group in yaml_metric_groups:
            if yaml_metric_groups[metric_group]["fetch"]:
                fetched_metric_groups.append(metric_group)
        context = client.metrics_contexts.create(
            {"anticipated-frequency-seconds": 15,
             "metric-groups": fetched_metric_groups})
        return context
    except zhmcclient.ConnectionError as exc:
        raise ConnectionError("Connection error using IP address {} defined "
                              "in HMC credentials file {}: {}".
                              format(session.host, filename, exc))
    except zhmcclient.AuthError as exc:
        raise AuthError("Authentication error when logging on to the "
                        "HMC at {} using userid '{}' defined in HMC "
                        "credentials file {}: {}".
                        format(session.host, session.userid, filename,
                               exc))
    except zhmcclient.Error as exc:
        raise OtherError("Error returned from HMC at {}: {}".
                         format(session.host, exc))


def delete_metrics_context(session, context):
    """The previously created context must also be deleted.
    Takes the session and context.
    Omitting this deletion may have unintended consequences.
    """
    # Destruction should not be attempted if context/session were not created
    if context:
        context.delete()
    if session:
        session.logoff()


def retrieve_metrics(context):
    """Retrieve metrics from the Z HMC.
    Takes the metrics context.
    Returns a dictionary of collected metrics.
    """
    retrieved_metrics = context.get_metrics()
    metrics_object = zhmcclient.MetricsResponse(context, retrieved_metrics)
    # Anatomy: metric group, resource (e.g. CPC), metric & value
    arranged_metrics = {}
    for metric_group_value in metrics_object.metric_group_values:
        arranged_metrics[metric_group_value.name] = {}
        for object_value in metric_group_value.object_values:
            resource_name = object_value.resource.name
            arranged_metrics[metric_group_value.name][resource_name] = {}
            for metrics_name in object_value.metrics:
                arranged_metrics[metric_group_value.name][resource_name][
                    metrics_name] = (object_value.metrics[metrics_name])
    return arranged_metrics


def format_unknown_metric(name):
    """Puts some generic formatting to an unknown metric.
    Takes the name.
    Returns a dictionary with the percent value, the exporter name, and the
    exporter description.
    """
    formatted_info = {"percent": False,
                      "exporter_name": name.replace("-", "_"),
                      "exporter_desc": name.replace("-", " ")}
    matches = re.findall(r".*-usage", name)
    # If it is a percent value
    if matches != []:
        formatted_info["percent"] = True
        formatted_info["exporter_name"] += "_ratio"
    return formatted_info


def identify_incoming_metrics(incoming_metrics, yaml_metrics, filename):
    """Ensures all metrics that come from the HMC are known.
    Takes the exported dictionary, the known metrics from the YAML file, and
    the name of the YAML file for error output.
    Returns the (possibly modified) metrics.
    """
    for metric_group in incoming_metrics:
        for resource in incoming_metrics[metric_group]:
            for metric in incoming_metrics[metric_group][resource]:
                if metric not in yaml_metrics[metric_group]:
                    yaml_metrics[metric_group][metric] = (
                        format_unknown_metric(metric))
                    warnings.warn("Metric '{}' returned by the HMC is not "
                                  "defined in metric definition file {} - "
                                  "consider adding it".
                                  format(metric, filename))
    return yaml_metrics


def add_families(yaml_metric_groups, yaml_metrics):
    """Add all metrics as label groups.
    Takes the known metric groups and the (possibly expanded by
    identify_incoming_metrics) known metrics, both from the YAML file.
    Returns a dictionary with these families.
    """
    # Anatomy: metric group, metric, family object
    family_objects = {}
    for metric_group in yaml_metrics:
        family_objects[metric_group] = {}
        for metric in yaml_metrics[metric_group]:
            family_name = "zhmc_{}_{}".format(
                yaml_metric_groups[metric_group]["prefix"],
                yaml_metrics[metric_group][metric]["exporter_name"])
            family_objects[metric_group][metric] = GaugeMetricFamily(
                family_name,
                yaml_metrics[metric_group][metric]["exporter_desc"],
                labels=["resource"])
    return family_objects


def store_metrics(retrieved_metrics, yaml_metrics, family_objects):
    """Store the metrics in the families to be exported.
    Takes the retrieved metrics, the known metrics from the YAML file, and the
    previously created families.
    Returns the dictionary with the metrics inserted.
    """
    for metric_group in retrieved_metrics:
        for resource in retrieved_metrics[metric_group]:
            for metric in retrieved_metrics[metric_group][resource]:
                # ZHMC: 100% means 100, Prometheus: 100% means 1
                if yaml_metrics[metric_group][metric]["percent"]:
                    retrieved_metrics[metric_group][resource][metric] /= 100
                family_objects[metric_group][metric].add_metric(
                    [resource],
                    retrieved_metrics[metric_group][resource][metric])
    return family_objects


class ZHMCUsageCollector():
    # pylint: disable=too-few-public-methods
    """Collects the usage for exporting."""

    def __init__(self, yaml_creds, session, context, yaml_metric_groups,
                 yaml_metrics, filename_metrics, filename_creds):
        self.session = session
        self.context = context
        self.yaml_creds = yaml_creds
        self.yaml_metric_groups = yaml_metric_groups
        self.yaml_metrics = yaml_metrics
        self.filename_metrics = filename_metrics
        self.filename_creds = filename_creds

    def collect(self):
        """Yield the metrics for exporting.
        Uses the context, the metric groups and the metrics from the YAML file,
        and the name of the YAML file for error output.
        """
        try:
            retrieved_metrics = retrieve_metrics(self.context)
        except zhmcclient.HTTPError as exc:
            if exc.http_status == 404 and exc.reason == 1:
                # Disable this line because it leads sometimes to
                # an exception within the exception handling.
                # delete_metrics_context(self.session, self.context)
                self.session = create_session(self.yaml_creds)
                self.context = create_metrics_context(self.session,
                                                      self.yaml_metric_groups,
                                                      self.filename_creds)
                retrieved_metrics = retrieve_metrics(self.context)
            else:
                raise
        self.yaml_metrics = identify_incoming_metrics(retrieved_metrics,
                                                      self.yaml_metrics,
                                                      self.filename_metrics)
        family_objects = add_families(self.yaml_metric_groups,
                                      self.yaml_metrics)
        family_objects = store_metrics(retrieved_metrics, self.yaml_metrics,
                                       family_objects)

        # Yield all groups
        for metric_group in family_objects:
            for metric in family_objects[metric_group]:
                yield family_objects[metric_group][metric]


def main():
    """Puts the exporter together."""
    # If the session and context keys are not created, their destruction
    # should not be attempted.
    session = False
    context = False
    try:
        args = parse_args(sys.argv[1:])
        if args.help_creds:
            help_creds()
            sys.exit(0)
        if args.help_metrics:
            help_metrics()
            sys.exit(0)
        try:
            raw_yaml_creds = parse_yaml_file(args.c, 'HMC credentials file')
        # These will be thrown upon wrong user input
        # The user should not see a traceback then
        except (PermissionError, FileNotFoundError) as error_message:
            raise ImproperExit(error_message)
        try:
            yaml_creds = parse_yaml_sections(raw_yaml_creds, ("metrics",),
                                             args.c)[0]
        except (AttributeError, YAMLInfoNotFoundError) as error_message:
            raise ImproperExit(error_message)
        try:
            check_creds_yaml(yaml_creds, args.c)
        except YAMLInfoNotFoundError as error_message:
            raise ImproperExit(error_message)
        try:
            raw_yaml_metrics = parse_yaml_file(args.m, 'metric definition file')
        except (PermissionError, FileNotFoundError) as error_message:
            raise ImproperExit(error_message)
        try:
            parsed_yaml_sections = parse_yaml_sections(
                raw_yaml_metrics, ("metric_groups", "metrics"), args.m)
            yaml_metric_groups = parsed_yaml_sections[0]
            yaml_metrics = parsed_yaml_sections[1]
        except (AttributeError, YAMLInfoNotFoundError) as error_message:
            raise ImproperExit(error_message)
        try:
            check_metrics_yaml(yaml_metric_groups, yaml_metrics, args.m)
        except YAMLInfoNotFoundError as error_message:
            raise ImproperExit(error_message)
        session = create_session(yaml_creds)
        try:
            context = create_metrics_context(session, yaml_metric_groups,
                                             args.c)
        except (ConnectionError, AuthError, OtherError) as error_message:
            raise ImproperExit(error_message)
        REGISTRY.register(ZHMCUsageCollector(yaml_creds, session, context,
                                             yaml_metric_groups,
                                             yaml_metrics, args.m, args.c))
        start_http_server(int(args.p))
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                raise ProperExit
    except KeyboardInterrupt:
        print("Operation interrupted before server start.")
        delete_metrics_context(session, context)
        sys.exit(1)
    except ImproperExit as error_message:
        print("Error: {}".format(error_message))
        delete_metrics_context(session, context)
        sys.exit(1)
    except ProperExit:
        print("Operation interrupted after server start.")
        delete_metrics_context(session, context)
        sys.exit(0)


if __name__ == "__main__":
    main()
