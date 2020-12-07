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
import os
import re
import time
import warnings
from contextlib import contextmanager

import urllib3
import yaml
import jsonschema
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


def parse_yaml_file(yamlfile, name, schemafilename=None):
    """
    Returns the parsed content of a YAML file as a Python object.
    Optionally validates against a specified JSON schema file in YAML format.

    Raises:
        ImproperExit
    """

    try:
        with open(yamlfile, "r") as fp:
            yaml_obj = yaml.safe_load(fp)
    except FileNotFoundError as exc:
        new_exc = ImproperExit(
            "Cannot find {} {}: {}".
            format(name, yamlfile, exc))
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc
    except PermissionError as exc:
        new_exc = ImproperExit(
            "Permission error reading {} {}: {}".
            format(name, yamlfile, exc))
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc
    except yaml.YAMLError as exc:
        new_exc = ImproperExit(
            "YAML error reading {} {}: {}".
            format(name, yamlfile, exc))
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc

    if schemafilename:

        schemafile = os.path.join(
            os.path.dirname(__file__), 'schemas', schemafilename)
        try:
            with open(schemafile, 'r') as fp:
                schema = yaml.safe_load(fp)
        except FileNotFoundError as exc:
            new_exc = ImproperExit(
                "Internal error: Cannot find schema file {}: {}".
                format(schemafile, exc))
            new_exc.__cause__ = None  # pylint: disable=invalid-name
            raise new_exc
        except PermissionError as exc:
            new_exc = ImproperExit(
                "Internal error: Permission error reading schema file {}: {}".
                format(schemafile, exc))
            new_exc.__cause__ = None  # pylint: disable=invalid-name
            raise new_exc
        except yaml.YAMLError as exc:
            new_exc = ImproperExit(
                "Internal error: YAML error reading schema file {}: {}".
                format(schemafile, exc))
            new_exc.__cause__ = None  # pylint: disable=invalid-name
            raise new_exc

        try:
            jsonschema.validate(yaml_obj, schema)
        except jsonschema.exceptions.SchemaError as exc:
            new_exc = ImproperExit(
                "Internal error: Invalid JSON schema file {}: {}".
                format(schemafile, exc))
            new_exc.__cause__ = None
            raise new_exc
        except jsonschema.exceptions.ValidationError as exc:
            new_exc = ImproperExit(
                "Schema validation of {} {} failed on element '{}': {}".
                format(name, yamlfile,
                       '.'.join(str(e) for e in exc.absolute_path), exc))
            new_exc.__cause__ = None
            raise new_exc

    return yaml_obj


def split_version(version_str, pad_to):
    """
    Return a tuple with the version parts as integers.

    Parameters:

      version_str (string): Version string, where the parts are separated by
        dot. The version parts must be decimal numbers. Example: '2.14'

      pad_to (int): Minimum number of version parts to return, padding the
        least significant version parts with 0. Example: '2.14' padded to
        3 results in (2, 14, 0).

    Returns:

      tuple(int, ...): Tuple of version parts, as integers.
    """
    version_info = []
    for v in version_str.strip('"\'').split('.'):
        if v == '':
            v = 0
        vint = int(v)  # May raise ValueError
        version_info.append(vint)
    while len(version_info) < pad_to:
        version_info.append(0)
        pad_to -= 1
    return tuple(version_info)


MNU_PATTERN = r'\d+(?:\.\d+(?:\.\d+)?)?'  # M.N.U
COND_PATTERN = '^(.*?)("{mnu}"|\'{mnu}\')(.*)$'.format(mnu=MNU_PATTERN)
COND_PATTERN = re.compile(COND_PATTERN)


def eval_condition(condition, hmc_version):
    """
    Evaluate a condition expression and return a boolean indicating whether
    the condition is true.

    Any version string in the condition expression is converted to a tuple of
    integers before evaluating the expression.

    Parameters:

      condition (string): Python expression to evaluate as a condition. The
        remaining parameters are valid variables to use in the expression.

      hmc_version (string): Expression variable: HMC version as a string.

    Returns:

      bool: Evaluated condition
    """
    hmc_version = split_version(hmc_version, 3)
    while True:
        m = COND_PATTERN.match(condition)
        if m is None:
            break
        condition = "{}{}{}".format(
            m.group(1), split_version(m.group(2), 3), m.group(3))
    # pylint: disable=eval-used
    condition = eval(condition, None, dict(hmc_version=hmc_version))
    return condition


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


def create_metrics_context(
        session, yaml_metric_groups, hmccreds_filename, hmc_version):
    """Creating a context is mandatory for reading metrics from the Z HMC.
    Takes the session, the metric_groups dictionary from the metrics YAML file
    for fetch/do not fetch information, and the name of the YAML file for error
    output.
    Returns the context.
    """
    fetched_metric_groups = []
    for metric_group in yaml_metric_groups:
        mg_dict = yaml_metric_groups[metric_group]
        # fetch is required in the metrics schema:
        fetch = mg_dict["fetch"]
        # if is optional in the metrics schema:
        if fetch and "if" in mg_dict:
            fetch = eval_condition(mg_dict["if"], hmc_version)
        if fetch:
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
                         metrics_filename, extra_labels,
                         resource_cache=None):
    """
    Go through all retrieved metrics and build the Prometheus Family objects.

    Returns a dictionary of Prometheus Family objects with the following
    structure:

      family_name:
        GaugeMetricFamily object
    """

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
            labels = dict(extra_labels)
            # labels is optional in the metrics schema:
            default_labels = [dict(name='resource', value='resource')]
            yaml_labels = yaml_metric_group.get('labels', default_labels)
            for item in yaml_labels:
                # name, value are required in the metrics schema:
                label_name = item['name']
                item_value = item['value']
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
                # exporter_name is required in the metrics schema:
                if not yaml_metric["exporter_name"]:
                    continue

                # Transform HMC percentages (value 100 means 100% = 1) to
                # Prometheus values (value 1 means 100% = 1)
                # percent is optional in the metrics schema:
                if yaml_metric.get("percent", False):
                    metric_value /= 100

                # Create a Family object, if needed
                # prefix,exporter_name are required in the metrics schema:
                family_name = "zhmc_{}_{}".format(
                    yaml_metric_group["prefix"],
                    yaml_metric["exporter_name"])
                try:
                    family_object = family_objects[family_name]
                except KeyError:
                    # exporter_desc is required in the metrics schema:
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
                 yaml_metrics, extra_labels, filename_metrics,
                 filename_creds, resource_cache, hmc_version):
        self.session = session
        self.context = context
        self.yaml_creds = yaml_creds
        self.yaml_metric_groups = yaml_metric_groups
        self.yaml_metrics = yaml_metrics
        self.extra_labels = extra_labels
        self.filename_metrics = filename_metrics
        self.filename_creds = filename_creds
        self.resource_cache = resource_cache
        self.hmc_version = hmc_version

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
                        self.filename_creds, self.hmc_version)
                    verbose2("Fetching metrics from HMC")
                    metrics_object = retrieve_metrics(self.context)
                else:
                    raise

            verbose2("Building family objects")
            family_objects = build_family_objects(metrics_object,
                                                  self.yaml_metric_groups,
                                                  self.yaml_metrics,
                                                  self.filename_metrics,
                                                  self.extra_labels,
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
        yaml_creds_content = parse_yaml_file(
            args.c, 'HMC credentials file', 'hmccreds_schema.yaml')
        # metrics is required in the metrics schema:
        yaml_creds = yaml_creds_content["metrics"]
        # extra_labels is optional in the metrics schema:
        yaml_extra_labels = yaml_creds_content.get("extra_labels", [])

        verbose("Parsing metric definition file: {}".format(args.m))
        yaml_metric_content = parse_yaml_file(
            args.m, 'metric definition file', 'metrics_schema.yaml')
        # metric_groups and metrics are required in the metrics schema:
        yaml_metric_groups = yaml_metric_content['metric_groups']
        yaml_metrics = yaml_metric_content['metrics']

        # Unregister the default collectors (Python, Platform)
        if hasattr(REGISTRY, '_collector_to_names'):
            # pylint: disable=protected-access
            for coll in list(REGISTRY._collector_to_names.keys()):
                REGISTRY.unregister(coll)

        # hmc is required in the HMC creds schema:
        verbose("Creating a session with HMC {}".format(yaml_creds['hmc']))
        session = create_session(yaml_creds)

        hmc_version = get_hmc_version(session, args.c)
        verbose("HMC version: {}".format(hmc_version))

        try:
            context = create_metrics_context(session, yaml_metric_groups,
                                             args.c, hmc_version)
        except (ConnectionError, AuthError, OtherError) as exc:
            raise ImproperExit(exc)

        extra_labels = dict()
        for item in yaml_extra_labels:
            # name, value are required in the HMC creds schema:
            extra_labels[item['name']] = item['value']
        extra_labels_str = ','.join(
            ['{}="{}"'.format(k, v) for k, v in extra_labels.items()])
        verbose("Using extra labels: {}".format(extra_labels_str))

        resource_cache = ResourceCache()
        coll = ZHMCUsageCollector(
            yaml_creds, session, context, yaml_metric_groups, yaml_metrics,
            extra_labels, args.m, args.c, resource_cache, hmc_version)

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
    except ImproperExit as exc:
        print("Error: {}".format(exc))
        delete_metrics_context(session, context)
        sys.exit(1)
    except ProperExit:
        print("Exporter interrupted after server start.")
        delete_metrics_context(session, context)
        sys.exit(0)


if __name__ == "__main__":
    main()
