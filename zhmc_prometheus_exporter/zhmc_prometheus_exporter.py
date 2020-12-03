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
IBM Z HMC Prometheus Exporter
"""

import argparse
import sys
import time
import ipaddress
import warnings
from contextlib import contextmanager
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


@contextmanager
def zhmc_exceptions(session, hmccreds_filename):
    # pylint: disable=invalid-name
    """
    Context manager that handles zhmcclient exceptions by raising the
    appropriate exporter exceptions.

    Example::

        with zhmc_exceptions(session, hmccreds_filename):
            client = zhmcclient.Client(session)
            version_info = client.version_info()
    """
    try:
        yield
    except zhmcclient.ConnectionError as exc:
        raise ConnectionError("Connection error using IP address {} defined "
                              "in HMC credentials file {}: {}".
                              format(session.host, hmccreds_filename, exc))
    except zhmcclient.AuthError as exc:
        raise AuthError("Authentication error when logging on to the "
                        "HMC at {} using userid '{}' defined in HMC "
                        "credentials file {}: {}".
                        format(session.host, session.userid, hmccreds_filename,
                               exc))
    except zhmcclient.Error as exc:
        raise OtherError("Error returned from HMC at {}: {}".
                         format(session.host, exc))


def parse_args(args):
    """Parses the CLI arguments."""
    parser = argparse.ArgumentParser(
        description="IBM Z HMC Exporter - a Prometheus exporter for metrics "
        "from the IBM Z HMC")
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
    parser.add_argument("-p", metavar="PORT",
                        default="9291",
                        help="port for exporting. Default: 9291")
    parser.add_argument("--verbose", "-v", action='count', default=0,
                        help="increase the verbosity level (max: 2)")
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

extra_labels:
  - name: pod
    value: mypod
""")


def help_metrics():
    """
    Print help for metric definition file.
    """
    print("""
Help for metric definition file

The metric definition file is a YAML file that defines which metrics are
exported to prometheus and under which names.

The following example shows a valid metric definition file that defines
a small subset of metrics and metric groups for DPM mode to be exported. For
more details and a full list of metrics and metric groups, see the
documentation at https://zhmc-prometheus-exporter.readthedocs.io/.

---
metric_groups:
  partition-usage:
    prefix: partition
    fetch: true
    labels:
      - name: cpc
        value: resource.parent
      - name: partition
        value: resource
  # ...
metrics:
  partition-usage:
    processor-usage:
      percent: true
      exporter_name: processor_usage_ratio
      exporter_desc: Usage ratio across all processors of the partition
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
                                            format(percent, metric,
                                                   metric_group, filename))
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


def get_hmc_version(session, hmccreds_filename):
    """
    Return the HMC version as a string "v.r.m".
    """
    with zhmc_exceptions(session, hmccreds_filename):
        client = zhmcclient.Client(session)
        version_dict = client.query_api_version()
    hmc_version = version_dict['hmc-version']
    return hmc_version


def create_metrics_context(session, yaml_metric_groups, hmccreds_filename):
    """Creating a context is mandatory for reading metrics from the Z HMC.
    Takes the session, the metric_groups dictionary from the metrics YAML file
    for fetch/do not fetch information, and the name of the YAML file for error
    output.
    Returns the context.
    """
    fetched_metric_groups = []
    for metric_group in yaml_metric_groups:
        if yaml_metric_groups[metric_group]["fetch"]:
            fetched_metric_groups.append(metric_group)
    verbose("Creating a metrics context on the HMC for metric groups:")
    for metric_group in fetched_metric_groups:
        verbose("  {}".format(metric_group))
    with zhmc_exceptions(session, hmccreds_filename):
        client = zhmcclient.Client(session)
        context = client.metrics_contexts.create(
            {"anticipated-frequency-seconds": 15,
             "metric-groups": fetched_metric_groups})
    return context


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
    """
    Retrieve metrics from the Z HMC.
    Takes the metrics context.
    Returns a zhmcclient.MetricsResponse object.
    """
    retrieved_metrics = context.get_metrics()
    metrics_object = zhmcclient.MetricsResponse(context, retrieved_metrics)
    return metrics_object


class ResourceCache(object):
    # pylint: disable=too-few-public-methods
    """
    Cache for zhmcclient resource objects to avoid having to look them up
    repeatedly.
    """

    def __init__(self):
        self._resources = {}  # dict URI -> Resource object

    def resource(self, uri, object_value):
        """
        Return the zhmcclient resource object for the URI, updating the cache
        if not present.
        """
        try:
            _resource = self._resources[uri]
        except KeyError:
            verbose2("Finding resource for {}".format(uri))
            _resource = object_value.resource  # Takes time to find on HMC
            self._resources[uri] = _resource
        return _resource


def build_family_objects(metrics_object, yaml_metric_groups, yaml_metrics,
                         metrics_filename, yaml_extra_labels,
                         resource_cache=None):
    """
    Go through all retrieved metrics and build the Prometheus Family objects.

    Returns a dictionary of Prometheus Family objects with the following
    structure:

      family_name:
        GaugeMetricFamily object
    """

    extra_labels = dict()
    for item in yaml_extra_labels:
        # name, value assumed to be present for now - will be validated once
        # schema validation is implemented.
        extra_labels[item['name']] = item['value']
    extra_labels_str = ','.join(
        ['{}="{}"'.format(k, v) for k, v in extra_labels.items()])
    verbose("Using extra labels: {}".format(extra_labels_str))

    family_objects = {}
    for metric_group_value in metrics_object.metric_group_values:
        metric_group = metric_group_value.name
        try:
            yaml_metric_group = yaml_metric_groups[metric_group]
        except KeyError:
            warnings.warn("Skipping metric group '{}' returned by the HMC "
                          "that is not defined in the 'metric_groups' section "
                          "of metric definition file {}".
                          format(metric_group, metrics_filename))
            continue  # Skip this metric group

        for object_value in metric_group_value.object_values:
            if resource_cache:
                resource = resource_cache.resource(
                    object_value.resource_uri, object_value)
            else:
                resource = object_value.resource
            metric_values = object_value.metrics

            # Calculate the resource labels:
            # metric_groups:
            #   {metric}:
            #     labels:
            #       - name: partition  # default: resource
            #         value: resource  # default: resource
            yaml_labels = yaml_metric_group.get('labels', None)
            if not yaml_labels:
                yaml_labels = [{}]
            labels = dict(extra_labels)
            for item in yaml_labels:
                label_name = item.get('name', 'resource')
                item_value = item.get('value', 'resource')
                if item_value == 'resource':
                    label_value = str(resource.name)
                elif item_value == 'resource.parent':
                    label_value = str(resource.manager.parent.name)
                elif item_value == 'resource.parent.parent':
                    label_value = \
                        str(resource.manager.parent.manager.parent.name)
                else:
                    label_value = str(metric_values.get(item_value, 'unknown'))
                labels[label_name] = label_value

            for metric in metric_values:
                try:
                    yaml_metric = yaml_metrics[metric_group][metric]
                except KeyError:
                    warnings.warn("Skipping metric '{}' of metric group '{}' "
                                  "returned by the HMC that is not defined in "
                                  "the 'metrics' section of metric definition "
                                  "file {}".
                                  format(metric, metric_group,
                                         metrics_filename))
                    continue  # Skip this metric

                metric_value = metric_values[metric]

                # Skip metrics with the special value -1 (which indicates that
                # the resource does not exist)
                if metric_value == -1:
                    continue

                # Skip metrics that are defined to be ignored
                if not yaml_metric.get("exporter_name", None):
                    continue

                # Transform HMC percentages (value 100 means 100% = 1) to
                # Prometheus values (value 1 means 100% = 1)
                if yaml_metric.get("percent", False):
                    metric_value /= 100

                # Create a Family object, if needed
                family_name = "zhmc_{}_{}".format(
                    yaml_metric_group["prefix"],
                    yaml_metric["exporter_name"])
                try:
                    family_object = family_objects[family_name]
                except KeyError:
                    family_object = GaugeMetricFamily(
                        family_name,
                        yaml_metric["exporter_desc"],
                        labels=list(labels.keys()))
                    family_objects[family_name] = family_object

                # Add the metric value to the Family object
                family_object.add_metric(list(labels.values()), metric_value)

    return family_objects


class ZHMCUsageCollector():
    # pylint: disable=too-few-public-methods
    """Collects the usage for exporting."""

    def __init__(self, yaml_creds, session, context, yaml_metric_groups,
                 yaml_metrics, yaml_extra_labels, filename_metrics,
                 filename_creds, resource_cache):
        self.session = session
        self.context = context
        self.yaml_creds = yaml_creds
        self.yaml_metric_groups = yaml_metric_groups
        self.yaml_metrics = yaml_metrics
        self.yaml_extra_labels = yaml_extra_labels
        self.filename_metrics = filename_metrics
        self.filename_creds = filename_creds
        self.resource_cache = resource_cache

    def collect(self):
        """Yield the metrics for exporting.
        Uses the context, the metric groups and the metrics from the YAML file,
        and the name of the YAML file for error output.
        """
        verbose2("Collecting metrics")

        with zhmc_exceptions(self.session, self.filename_creds):
            try:
                verbose2("Fetching metrics from HMC")
                metrics_object = retrieve_metrics(self.context)
            except zhmcclient.HTTPError as exc:
                if exc.http_status == 404 and exc.reason == 1:
                    # Disable this line because it leads sometimes to
                    # an exception within the exception handling.
                    # delete_metrics_context(self.session, self.context)
                    verbose2(" Recreating a metrics context on the HMC")
                    self.session = create_session(self.yaml_creds)
                    self.context = create_metrics_context(
                        self.session, self.yaml_metric_groups,
                        self.filename_creds)
                    verbose2("Fetching metrics from HMC")
                    metrics_object = retrieve_metrics(self.context)
                else:
                    raise

            verbose2("Building family objects")
            family_objects = build_family_objects(metrics_object,
                                                  self.yaml_metric_groups,
                                                  self.yaml_metrics,
                                                  self.filename_metrics,
                                                  self.yaml_extra_labels,
                                                  self.resource_cache)

        verbose2("Returning family objects")
        # Yield all family objects
        for family_name in family_objects:
            yield family_objects[family_name]

        verbose2("Done collecting metrics")


VERBOSE_LEVEL = 0


def verbose(message):
    """Print a message at verbosity level 1"""
    if VERBOSE_LEVEL >= 1:
        print(message)


def verbose2(message):
    """Print a message at verbosity level 2"""
    if VERBOSE_LEVEL >= 2:
        print(message)


def main():
    """Puts the exporter together."""
    # If the session and context keys are not created, their destruction
    # should not be attempted.

    global VERBOSE_LEVEL  # pylint: disable=global-statement

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
        VERBOSE_LEVEL = args.verbose

        verbose("Parsing HMC credentials file: {}".format(args.c))
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
        if "extra_labels" in raw_yaml_creds:
            try:
                yaml_extra_labels = parse_yaml_sections(
                    raw_yaml_creds, ("extra_labels",), args.c)[0]
            except (AttributeError, YAMLInfoNotFoundError) as error_message:
                raise ImproperExit(error_message)
        else:
            yaml_extra_labels = []

        verbose("Parsing metric definition file: {}".format(args.c))
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

        # Unregister the default collectors (Python, Platform)
        if hasattr(REGISTRY, '_collector_to_names'):
            # pylint: disable=protected-access
            for coll in list(REGISTRY._collector_to_names.keys()):
                REGISTRY.unregister(coll)

        verbose("Creating a session with HMC {}".format(yaml_creds['hmc']))
        session = create_session(yaml_creds)

        hmc_version = get_hmc_version(session, args.c)
        verbose("HMC version: {}".format(hmc_version))

        try:
            context = create_metrics_context(session, yaml_metric_groups,
                                             args.c)
        except (ConnectionError, AuthError, OtherError) as error_message:
            raise ImproperExit(error_message)

        resource_cache = ResourceCache()
        coll = ZHMCUsageCollector(
            yaml_creds, session, context, yaml_metric_groups, yaml_metrics,
            yaml_extra_labels, args.m, args.c, resource_cache)

        verbose("Registering the collector and performing first collection")
        REGISTRY.register(coll)  # Performs a first collection

        verbose("Starting the HTTP server on port {}".format(args.p))
        start_http_server(int(args.p))

        verbose("Exporter is up and running")
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                raise ProperExit
    except KeyboardInterrupt:
        print("Exporter interrupted before server start.")
        delete_metrics_context(session, context)
        sys.exit(1)
    except ImproperExit as error_message:
        print("Error: {}".format(error_message))
        delete_metrics_context(session, context)
        sys.exit(1)
    except ProperExit:
        print("Exporter interrupted after server start.")
        delete_metrics_context(session, context)
        sys.exit(0)


if __name__ == "__main__":
    main()
