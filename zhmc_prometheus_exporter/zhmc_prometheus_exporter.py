#!/usr/bin/env python3


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

"""A prometheus.io exporter for metrics from the Z Hardware Management Console
"""

import argparse
import sys
import time
import ipaddress
import warnings
import re
import yaml
import urllib3

import zhmcclient

from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY


class YAMLInfoNotFoundError(Exception):
    """A custom error that is raised when something that was expected in a
    YAML cannot be found.
    """
    pass


class ConnectTimeout(Exception):
    """Unwrapped from zhmcclient"""
    pass


class ServerAuthError(Exception):
    """Unwrapped from zhmcclient"""
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
    parser.add_argument("-p", metavar="PORT", default="9291", help="Port for "
                        "exporting (default 9291)")
    parser.add_argument("-c", metavar="CREDENTIALS", default="/etc/zhmc-"
                        "prometheus-exporter/hmccreds.yaml",
                        help="Credentials information (default /etc/zhmc-"
                        "prometheus-exporter/hmccreds.yaml)")
    parser.add_argument("-m", metavar="METRICS", default="/etc/zhmc-"
                        "prometheus-exporter/metrics.yaml", help="Credentials "
                        "information (default /etc/zhmc-prometheus-exporter/"
                        "metrics.yaml)")
    return parser.parse_args(args)


def parse_yaml_file(yamlfile):
    """Takes a YAML file name.
    Returns a parsed version of that file i.e. nests of dictionaries and lists.
    """
    try:
        with open(yamlfile, "r") as yamlcontent:
            return yaml.load(yamlcontent)
    except PermissionError:
        raise PermissionError("Permission error. Make sure you have "
                              "appropriate permissions to read from %s."
                              % yamlfile)
    except FileNotFoundError:
        raise FileNotFoundError("Error: File not found. It seems that %s "
                                "does not exist." % yamlfile)


def parse_yaml_sections(yamlcontent, sought_sections, filename):
    """Takes nests of dictionaries and lists, the required sections,
    and the name of the YAML file for error output.
    Returns a list of the parsed sections as dictionaries.
    """
    parsed_sections = []
    try:
        for sought_section in sought_sections:
            section = yamlcontent.get(sought_section, None)
            if section is None:
                raise YAMLInfoNotFoundError("Section %s not found in file %s."
                                            % (sought_section, filename))
            parsed_sections.append(section)
    except AttributeError:
        raise AttributeError("%s does not follow the YAML syntax" % filename)
    return parsed_sections


def check_creds_yaml(yaml_creds, filename):
    """Verify all required information in the credentials YAML file is given.
    Takes the dictionary retrieved from parse_yaml_sections and the name of
    the YAML file for error output.
    """
    if "hmc" not in yaml_creds:
        raise YAMLInfoNotFoundError("You did not specify the IP address of "
                                    "the HMC in %s." % filename)
    try:
        ipaddress.ip_address(yaml_creds["hmc"])
    except ValueError:
        raise YAMLInfoNotFoundError("You did not specify a correct IP "
                                    "address in %s." % filename)
    if "userid" not in yaml_creds:
        raise YAMLInfoNotFoundError("You did not specify a user ID in %s."
                                    % filename)
    if "password" not in yaml_creds:
        raise YAMLInfoNotFoundError("You did not specify a password in %s."
                                    % filename)


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
            raise YAMLInfoNotFoundError("In %s, you did not specify a prefix "
                                        "for %s." % (filename, metric_group))
        if "fetch" not in yaml_metric_groups[metric_group]:
            raise YAMLInfoNotFoundError("In %s, you did not specify whether "
                                        "%s is to be fetched."
                                        % (filename, metric_group))
        if yaml_metric_groups[metric_group]["fetch"] not in (True, False):
            raise YAMLInfoNotFoundError("In %s, you did not specify whether "
                                        "%s is to be fetched with True or "
                                        "False." % (filename, metric_group))
    for metric_group in yaml_metrics:
        if metric_group not in yaml_metric_groups:
            raise YAMLInfoNotFoundError("In %s, you specified %s as a metric "
                                        "group, but you did not specify it "
                                        "within the metric_groups section."
                                        % (filename, metric_group))
        for metric in yaml_metrics[metric_group]:
            if "percent" not in yaml_metrics[metric_group][metric]:
                raise YAMLInfoNotFoundError("In %s, you did not specify "
                                            "whether %s is a percent value."
                                            % (filename, metric))
            if yaml_metrics[metric_group][metric]["percent"] not in (True,
                                                                     False):
                raise YAMLInfoNotFoundError("In %s, you did not specify "
                                            "whether %s is a percent value "
                                            "with True or False."
                                            % (filename, metric))
            if "exporter_name" not in yaml_metrics[metric_group][metric]:
                raise YAMLInfoNotFoundError("In %s, you did not specify an "
                                            "exporter name for %s."
                                            % (filename, metric))
            if "exporter_desc" not in yaml_metrics[metric_group][metric]:
                raise YAMLInfoNotFoundError("In %s, you did not specify an "
                                            "exporter description for %s."
                                            % (filename, metric))


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
    except zhmcclient.ConnectTimeout:
        raise ConnectTimeout("Time out. Ensure that you have access to the "
                             "HMC and that you have stored the correct IP "
                             "address in %s." % filename)
    except zhmcclient.ServerAuthError:
        raise ServerAuthError("Authentication error. Ensure that you have "
                              "stored a correct user ID-password combination "
                              "in %s." % filename)


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
                    # warnings does not handle multiline well
                    warning_str = ("Metric %s was not found. Consider "
                                   "adding it to your %s.")
                    warnings.warn(warning_str % (metric, filename))
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
            family_name = ("zhmc_" +
                           yaml_metric_groups[metric_group]["prefix"]
                           +
                           "_" +
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
                delete_metrics_context(self.session, self.context)
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
        try:
            raw_yaml_creds = parse_yaml_file(args.c)
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
            raw_yaml_metrics = parse_yaml_file(args.m)
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
        except (ConnectTimeout, ServerAuthError) as error_message:
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
        print(error_message)
        delete_metrics_context(session, context)
        sys.exit(1)
    except ProperExit:
        print("Operation interrupted after server start.")
        delete_metrics_context(session, context)
        sys.exit(0)


if __name__ == "__main__":
    main()
