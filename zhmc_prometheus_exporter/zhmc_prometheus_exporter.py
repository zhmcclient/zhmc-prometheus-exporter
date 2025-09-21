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
from datetime import datetime
import warnings
import logging
import logging.handlers
import traceback
import threading

import jinja2
import urllib3
from ruamel.yaml import YAML, YAMLError
import jsonschema
import zhmcclient

from ._exceptions import AuthError, OtherError, ProperExit, ImproperExit, \
    InvalidMetricDefinitionFile, EarlyExit, zhmc_exceptions
from ._exceptions import ConnectionError  # pylint: disable=redefined-builtin
from ._logging import PRINT_ALWAYS, PRINT_V, PRINT_VV, logprint, \
    VALID_LOG_DESTINATIONS, VALID_LOG_LEVELS, VALID_LOG_COMPONENTS, \
    DEFAULT_LOG_LEVEL, DEFAULT_LOG_COMP, DEFAULT_SYSLOG_FACILITY, \
    VALID_SYSLOG_FACILITIES, setup_logging
from ._resource_cache import ResourceCache
from .vendor.prometheus_client import start_http_server
from .vendor.prometheus_client.core import GaugeMetricFamily, \
    CounterMetricFamily, REGISTRY
from .vendor import prometheus_client_version
from ._version import __version__

__all__ = []

DEFAULT_CONFIG_FILE = '/etc/zhmc-prometheus-exporter/config.yaml'
DEFAULT_PORT = 9291

# Sleep time and hysteresis in property fetch thread
INITIAL_FETCH_SLEEP_TIME = 30
MIN_FETCH_SLEEP_TIME = 30
MAX_FETCH_SLEEP_TIME = 3600
FETCH_HYSTERESIS = 10

# Sleep time in seconds when retrying metrics retrieval
RETRY_SLEEP_TIME = 10

# HMC request/response truncation of data in log entries. 0 means no truncation.
LOG_CONTENT_TRUNCATE = 0


def parse_args(args):
    """Parses the CLI arguments."""

    parser = argparse.ArgumentParser(
        description="IBM Z HMC Exporter - a Prometheus exporter for metrics "
        "from the IBM Z HMC")
    parser.add_argument("-c", metavar="CONFIG_FILE",
                        default=DEFAULT_CONFIG_FILE,
                        help="path name of exporter config file. "
                        "Use --help-config for details. "
                        f"Default: {DEFAULT_CONFIG_FILE}")
    parser.add_argument("-p", metavar="PORT",
                        default=None,
                        help="port for exporting. Default: prometheus.port in "
                        "exporter config file")
    parser.add_argument("--log", dest='log_dest', metavar="DEST", default=None,
                        help="enable logging and set a log destination "
                        "({dests}). Default: no logging".
                        format(dests=', '.join(VALID_LOG_DESTINATIONS)))
    parser.add_argument("--log-comp", dest='log_complevels', action='append',
                        metavar="COMP[=LEVEL]", default=None,
                        help="set a logging level ({levels}, default: "
                        "{def_level}) for a component ({comps}). May be "
                        "specified multiple times; options add to the default "
                        "of: {def_comp}. Note that using log levels 'info' or "
                        "'debug' will produce continuously growing log output.".
                        format(levels=', '.join(VALID_LOG_LEVELS),
                               comps=', '.join(VALID_LOG_COMPONENTS),
                               def_level=DEFAULT_LOG_LEVEL,
                               def_comp=DEFAULT_LOG_COMP))
    parser.add_argument("--syslog-facility", metavar="TEXT",
                        default=DEFAULT_SYSLOG_FACILITY,
                        help="syslog facility ({slfs}) when logging to the "
                        "system log. Default: {def_slf}".
                        format(slfs=', '.join(VALID_SYSLOG_FACILITIES),
                               def_slf=DEFAULT_SYSLOG_FACILITY))
    parser.add_argument("--verbose", "-v", action='count', default=0,
                        help="increase the verbosity level of terminal output "
                        "during startup of the exporter (max: 2). After the "
                        "exporter is up and running, no more terminal output "
                        "will be produced, except in the case of warnings or "
                        "connection issues.")
    parser.add_argument("--version", action='store_true',
                        help="show versions of exporter and zhmcclient library "
                        "and exit")
    parser.add_argument("--upgrade-config", action='store_true',
                        help="upgrade the exporter config file to the current "
                        "version of the exporter and exit")
    parser.add_argument("--help-config", action='store_true',
                        help="show help for exporter config file and exit")
    return parser.parse_args(args)


def print_version():
    """
    Print the version of this program and the zhmcclient library.
    """
    # pylint: disable=no-member
    print(f"zhmc_prometheus_exporter version: {__version__}\n"
          f"zhmcclient version: {zhmcclient.__version__}\n"
          f"prometheus_client (vendored) version: {prometheus_client_version}")


def help_config():
    """
    Print help for exporter config file.
    """
    print("""
Help for exporter config file

The exporter config file is a YAML file that specifies data for logging on
to the HMC, data for exporting to Prometheus, and data for controlling which
metric groups are exported.

The HMC userid must be authorized for object access permission to the resources
for which metrics are to be returned. Metrics of resources for which the userid
does not have object access permission will not be included in the result,
without raising an error.

The following example shows a complete exporter config file for the version 2
format. For more details, see the documentation at
https://zhmc-prometheus-exporter.readthedocs.io/.

---
# Version of config file format
version: 2

# Redundant HMCs and their credentials
hmcs:
  - host: 9.10.11.12
    userid: userid
    password: password
    # Note: The verify_cert parameter controls whether and how the HMC server
    #       certificate is validated by the exporter. For more details,
    #       see doc section 'HMC certificate'.
    # verify_cert: true           # (default) Validate using default CA certs
    # verify_cert: my_certs_file  # Validate using this CA certs file
    # verify_cert: my_certs_dir   # Validate using this CA certs directory
    # verify_cert: false          # Disable validation
    verify_cert: false

# Communication with Prometheus
prometheus:
  port: 9291

  # Note: Activating the following two parameters enables the use of HTTPS
  # server_cert_file: server_cert.pem
  # server_key_file: server_key.pem

  # Note: Activating the following parameter enables the use of mutual TLS
  # ca_cert_file: ca_certs.pem

# Additional user-defined labels to be added to all metrics
extra_labels:
  # - name: hmc
  #   value: "hmc_info['hmc-name']"
  # - name: pod
  #   value: "'mypod'"

# List of CPCs to export data for. Optional, default is all managed CPCs
cpcs:
  # - {cpc-name}

# Metric groups to be fetched
metric_groups:

  # Available for CPCs in classic mode
  cpc-usage-overview:
    export: true
  logical-partition-usage:
    export: true
  channel-usage:
    export: true
  crypto-usage:
    export: true
  flash-memory-usage:
    export: true
  roce-usage:
    export: true
  logical-partition-resource:
    export: true

  # Available for CPCs in DPM mode
  dpm-system-usage-overview:
    export: true
  partition-usage:
    export: true
  adapter-usage:
    export: true
  network-physical-adapter-port:
    export: true
  partition-attached-network-interface:
    export: true
  partition-resource:
    export: true
  storagegroup-resource:
    export: true
  storagevolume-resource:
    export: true
  adapter-resource:
    export: true

  # Available for CPCs in any mode
  zcpc-environmentals-and-power:
    export: true
  zcpc-processor-usage:
    export: true
  environmental-power-status:
    export: true
  cpc-resource:
    export: true
""")


def validate_option(option_name, option_value, allowed_values):
    """
    Validate the option value against the allowed option values
    and return the value, if it passes. raises EarlyExit otherwise.

    Raises:
      EarlyExit: Invalid command line usage.
    """
    if option_value not in allowed_values:
        raise EarlyExit(
            "Invalid value {val} for {opt} option. Allowed are: {allowed}".
            format(opt=option_name, val=option_value,
                   allowed=', '.join(allowed_values)))
    return option_value


def parse_yaml_file(yamlfile, name, schemafilename=None):
    """
    Returns the parsed content of a YAML file as a Python object.
    Optionally validates against a specified JSON schema file in YAML format.

    Raises:
        ImproperExit
    """

    yaml = YAML(typ='rt')
    try:
        with open(yamlfile, encoding='utf-8') as fp:
            yaml_obj = yaml.load(fp)
    except FileNotFoundError as exc:
        new_exc = ImproperExit(
            f"Cannot find {name} {yamlfile}: {exc}")
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc
    except PermissionError as exc:
        new_exc = ImproperExit(
            f"Permission error reading {name} {yamlfile}: {exc}")
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc
    except YAMLError as exc:
        new_exc = ImproperExit(
            f"YAML error reading {name} {yamlfile}: {exc}")
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc

    if schemafilename:

        yaml = YAML(typ='safe')
        schemafile = os.path.join(
            os.path.dirname(__file__), 'schemas', schemafilename)
        try:
            with open(schemafile, encoding='utf-8') as fp:
                schema = yaml.load(fp)
        except FileNotFoundError as exc:
            new_exc = ImproperExit(
                f"Internal error: Cannot find schema file {schemafile}: {exc}")
            new_exc.__cause__ = None  # pylint: disable=invalid-name
            raise new_exc
        except PermissionError as exc:
            new_exc = ImproperExit(
                "Internal error: Permission error reading schema file "
                f"{schemafile}: {exc}")
            new_exc.__cause__ = None  # pylint: disable=invalid-name
            raise new_exc
        except YAMLError as exc:
            new_exc = ImproperExit(
                "Internal error: YAML error reading schema file "
                f"{schemafile}: {exc}")
            new_exc.__cause__ = None  # pylint: disable=invalid-name
            raise new_exc

        try:
            jsonschema.validate(yaml_obj, schema)
        except jsonschema.exceptions.SchemaError as exc:
            new_exc = ImproperExit(
                f"Internal error: Invalid JSON schema file {schemafile}: "
                f"{exc}")
            new_exc.__cause__ = None
            raise new_exc
        except jsonschema.exceptions.ValidationError as exc:
            element_str = json_path_str(exc.absolute_path)
            new_exc = ImproperExit(
                f"Validation of {name} {yamlfile} failed on {element_str}: "
                f"{exc.message}")
            new_exc.__cause__ = None
            raise new_exc

    return yaml_obj


def write_yaml_file(yaml_obj, yamlfile, name):
    """
    Write a YAML object into a YAML file, overwriting any existing file.

    Raises:
        ImproperExit
    """
    yaml = YAML(typ='rt')
    try:
        with open(yamlfile, encoding='utf-8', mode='w') as fp:
            yaml.dump(yaml_obj, fp)
    except FileNotFoundError as exc:
        new_exc = ImproperExit(
            f"Cannot find {name} {yamlfile}: {exc}")
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc
    except PermissionError as exc:
        new_exc = ImproperExit(
            f"Permission error writing {name} {yamlfile}: {exc}")
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc
    except YAMLError as exc:
        new_exc = ImproperExit(
            f"YAML error writing {name} {yamlfile}: {exc}")
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc


def upgrade_config_dict(config_dict, config_filename, upgrade_config=False):
    """
    Upgrade the config dict to the current exporter version.
    """

    if 'metrics' not in config_dict and 'hmcs' not in config_dict:
        new_exc = ImproperExit(
            "The exporter config file must specify either the new 'hmcs' "
            "item or the old 'metrics' item, but it specifies none.")
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc

    if 'metrics' in config_dict and 'hmcs' in config_dict:
        new_exc = ImproperExit(
            "The exporter config file must specify either the new 'hmcs' "
            "item or the old 'metrics' item, but it specifies both.")
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc

    if 'version' in config_dict and config_dict['version'] != 2:
        new_exc = ImproperExit(
            "The exporter config file must have the version 2 format, "
            f"but it specifies the version {config_dict['version']} "
            "format.")
        new_exc.__cause__ = None  # pylint: disable=invalid-name
        raise new_exc

    if 'metrics' in config_dict and 'hmcs' not in config_dict:
        # Exporter config file has version 1

        if upgrade_config:
            logprint(logging.WARNING, PRINT_ALWAYS,
                     f"The exporter config file {config_filename} has the "
                     "old version 1 format and is now upgraded.")
        else:
            logprint(logging.WARNING, PRINT_ALWAYS,
                     f"The exporter config file {config_filename} has the "
                     "old version 1 format and is now internally upgraded "
                     "without persisting the changes to the file. Please "
                     "upgrade the file using the '--upgrade-config' option.")

        # Convert old format to new format
        config_dict.insert(0, key='version', value=2)

        old_creds = config_dict['metrics']
        hmc_item = {
            'host': old_creds['hmc'],
            'userid': old_creds['userid'],
            'password': old_creds['password'],
            'verify_cert': old_creds.get('verify_cert', True),
        }
        config_dict.insert(1, key='hmcs', value=[hmc_item])
        del config_dict['metrics']

        if 'metric_groups' not in config_dict:
            logprint(logging.INFO, PRINT_ALWAYS,
                     "Adding a 'metric_groups' item to the exporter "
                     "configuration that enables all metric groups.")
            config_dict['metric_groups'] = {
                'cpc-usage-overview': {'export': True},
                'logical-partition-usage': {'export': True},
                'channel-usage': {'export': True},
                'crypto-usage': {'export': True},
                'flash-memory-usage': {'export': True},
                'roce-usage': {'export': True},
                'logical-partition-resource': {'export': True},
                'dpm-system-usage-overview': {'export': True},
                'partition-usage': {'export': True},
                'adapter-usage': {'export': True},
                'network-physical-adapter-port': {'export': True},
                'partition-attached-network-interface': {'export': True},
                'partition-resource': {'export': True},
                'storagegroup-resource': {'export': True},
                'storagevolume-resource': {'export': True},
                'adapter-resource': {'export': True},
                'zcpc-environmentals-and-power': {'export': True},
                'zcpc-processor-usage': {'export': True},
                'environmental-power-status': {'export': True},
                'cpc-resource': {'export': True},
            }
    else:
        # Exporter config file has current version
        if upgrade_config:
            logprint(logging.WARNING, PRINT_ALWAYS,
                     f"The exporter config file {config_filename} has the "
                     "current version and is not being changed.")


def upgrade_config_file(config_filename):
    """
    Parse the exporter config file.

    Backlevel formats are dynamically upgraded to the current format (without
    changing the file).
    """

    config_dict = parse_yaml_file(
        config_filename, 'exporter config file', 'config_schema.yaml')
    upgrade_config_dict(config_dict, config_filename, upgrade_config=True)
    write_yaml_file(config_dict, config_filename, 'exporter config file')


def parse_config_file(config_filename):
    """
    Parse the exporter config file.

    Backlevel formats are internally upgraded to the current format (without
    changing the file).
    """

    config_dict = parse_yaml_file(
        config_filename, 'exporter config file', 'config_schema.yaml')
    upgrade_config_dict(config_dict, config_filename)
    return config_dict


def json_path_str(path_list):
    """
    Return a string with the path list in JSON path notation, except that
    the root element is not '$' but verbally expressed.
    """
    if not path_list:
        return "root elements"

    path_str = ""
    for p in path_list:
        if isinstance(p, int):
            path_str += f"[{p}]"
        else:
            path_str += f".{p}"
    if path_str.startswith('.'):
        path_str = path_str[1:]
    return f"element '{path_str}'"


def split_version(version_str_, pad_to):
    """
    Return a tuple from a version string, with the version parts as integers.

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
    for v in version_str_.strip('"\'').split('.'):
        if v == '':
            v = 0
        vint = int(v)  # May raise ValueError
        version_info.append(vint)
    while len(version_info) < pad_to:
        version_info.append(0)
        pad_to -= 1
    return tuple(version_info)


def version_str(version_tuple):
    """
    Return a version string from a version tuple.

    Parameters:

      version_tuple (tuple(int, ...)): Tuple of version parts, as integers.
        Example: (2, 14)

    Returns:

      str: Version string, e.g. '2.14'
    """
    vt = [str(v) for v in version_tuple]
    return '.'.join(vt)


MNU_PATTERN = r'\d+(?:\.\d+(?:\.\d+)?)?'  # M.N.U
COND_PATTERN = f'^(.*?)("{MNU_PATTERN}"|\'{MNU_PATTERN}\')(.*)$'
COND_PATTERN = re.compile(COND_PATTERN)


def resource_str(resource_obj):
    """
    Return a human readable string identifying the resource object, for
    messages.
    """
    res_class = resource_obj.properties['class']
    if res_class == 'cpc':
        res_str = f"CPC '{resource_obj.name}'"
    elif res_class in ('partition', 'logical-partition'):
        res_str = "partition '{}' on CPC '{}'". \
            format(resource_obj.name, resource_obj.manager.parent.name)
    else:
        raise ValueError(f"Resource class {res_class} is not supported")
    return res_str


def eval_condition(
        item_str, condition, hmc_version, hmc_api_version, hmc_features,
        se_version, se_features, resource_obj):
    """
    Evaluate a Python expression as a condition and return a boolean indicating
    whether the condition is true.

    Any M.N.U version strings in the condition expression are converted to a
    tuple of integers before evaluating the expression.

    Parameters:

      item_str (string): A string that identifies that item the condition
        is on, for use in messages.

      condition (string): Python expression to evaluate as a condition. The
        remaining parameters are valid variables to use in the expression.

      hmc_version (tuple(M,N,U)): Expression variable: HMC version.

      hmc_api_version (tuple(M,N)): Expression variable: HMC API version.

      hmc_features (list of string): Expression variable: List of the names of
        the API features supported by the HMC. Will be empty before HMC API
        version 4.10.

      se_version (tuple(M,N,U)): Expression variable: SE/CPC version, or None
        for metric groups or when there is no CPC context for the metric.

      se_features (list of string): Expression variable: List of the names of
        the API features supported by the SE/CPC (will be empty before HMC API
        version 4.10 or before SE version 2.16.0), or None for metric groups
        or when there is no CPC context for the metric.

      resource_obj (zhmcclient.BaseResource): Expression variable: The resource
        object for metrics, or None for metric groups.

    Returns:

      bool: Evaluated condition
    """
    org_condition = condition
    if se_features is None:
        se_features = []
    if hmc_features is None:
        hmc_features = []

    # Convert literal strings 'M.N.U' in condition to tuple syntax (M, N, U)
    while True:
        m = COND_PATTERN.match(condition)
        if m is None:
            break
        condition = "{}{}{}".format(
            m.group(1), split_version(m.group(2), 3), m.group(3))

    # The variables that can be used in the expression
    eval_vars = dict(
        __builtins__={},
        hmc_version=hmc_version,
        hmc_api_version=hmc_api_version,
        hmc_features=hmc_features,
    )
    if resource_obj:
        # In an export-condition (not in a fetch-condition)
        eval_vars.update(dict(
            se_version=se_version,
            se_features=se_features,
            resource_obj=resource_obj,
        ))

    # --- begin debug code - enable in case of issues with conditions
    # var_dict = dict(eval_vars)
    # if resource_obj:
    #     var_dict['resource_obj'] = "{rt} {rn!r}".format(
    #         rt=resource_obj.__class__.__name__, rn=resource_obj.name)
    # print("Debug: Evaluating 'if' condition: {c!r} with variables: {vd}".
    #       format(c=condition, vd=var_dict))
    # --- end debug code

    try:
        # pylint: disable=eval-used
        result = eval(condition, eval_vars, None)  # nosec: B307
    except Exception as exc:  # pylint: disable=broad-exception-caught
        tb_str = traceback.format_tb(exc.__traceback__, limit=-1)[0]
        warnings.warn(
            f"Not providing {item_str} because its condition "
            f"{org_condition!r} does not properly evaluate: "
            f"{exc.__class__.__name__}: {exc}\n{tb_str}")
        return False

    # --- begin debug code - enable in case of issues with conditions
    # print(f"Debug: Result of 'if' condition: {result!r}")
    # --- end debug code

    return result


def create_session(config_dict, config_filename):
    """
    Create a zhmcclient session to the HMC.

    Parameters:
      config_dict (dict): Content of the exporter config file.
      config_filename (string): Path name of the exporter config file.

    Returns:
      zhmcclient.Session
    """
    # These warnings do not concern us
    urllib3.disable_warnings()

    hmcs = config_dict["hmcs"]
    if not hmcs:
        raise ImproperExit(
            "The 'hmcs' item in the exporter config file does not specify "
            "any HMCs.")
    hmc_dict = hmcs[0]

    logprint(logging.INFO, PRINT_V,
             f"HMC host: {hmc_dict['host']}")
    logprint(logging.INFO, PRINT_V,
             f"HMC userid: {hmc_dict['userid']}")

    verify_cert = hmc_dict.get("verify_cert", True)
    if isinstance(verify_cert, str):
        if not os.path.isabs(verify_cert):
            verify_cert = os.path.join(
                os.path.dirname(config_filename), verify_cert)
    logprint(logging.INFO, PRINT_V,
             f"HMC certificate validation: {verify_cert}")

    # Retry / timeout configuration for zhmcclient
    rt_parms = hmc_dict.get("retry_timeout", {})
    rt_config = zhmcclient.RetryTimeoutConfig(
        connect_timeout=rt_parms.get("connect_timeout", 10),
        connect_retries=rt_parms.get("connect_retries", 2),
        read_timeout=rt_parms.get("read_timeout", 900),
        read_retries=rt_parms.get("read_retries", 2),
        max_redirects=zhmcclient.DEFAULT_MAX_REDIRECTS,
        operation_timeout=rt_parms.get(
            "operation_timeout", zhmcclient.DEFAULT_OPERATION_TIMEOUT),
        status_timeout=rt_parms.get(
            "status_timeout", zhmcclient.DEFAULT_STATUS_TIMEOUT),
        name_uri_cache_timetolive=zhmcclient.DEFAULT_NAME_URI_CACHE_TIMETOLIVE,
        log_content_truncate=LOG_CONTENT_TRUNCATE,
    )

    logprint(logging.INFO, PRINT_V,
             "Timeout/retry configuration: "
             f"connect: {rt_config.connect_timeout} sec / "
             f"{rt_config.connect_retries} retries, "
             f"read: {rt_config.read_timeout} sec / "
             f"{rt_config.read_retries} retries.")

    truncate_str = f"{rt_config.log_content_truncate} B" if \
        rt_config.log_content_truncate > 0 else 'none'
    logprint(logging.INFO, PRINT_V,
             f"Log truncation: {truncate_str}")

    session = zhmcclient.Session(hmc_dict["host"],
                                 hmc_dict["userid"],
                                 hmc_dict["password"],
                                 verify_cert=verify_cert,
                                 retry_timeout_config=rt_config)
    return session


def get_hmc_info(session):
    """
    Return the result of the 'Query API Version' operation. This includes
    the HMC version, HMC name and other data. For details, see the operation's
    result description in the HMC WS API book.

    Returns:
        dict: Dict of properties returned from the 'Query API Version'
        operation. Some important properties are:
        - api-major-version (int) : Major part of the HMC API version
        - api-minor-version (int) : Minor part of the HMC API version
        - hmc-version (string): HMC version, as a string of the form 'M.N.U'.

    Raises: zhmccclient exceptions
    """
    client = zhmcclient.Client(session)
    hmc_info = client.query_api_version()
    return hmc_info


def exported_metric_groups(
        config_dict, yaml_metric_groups, hmc_version, hmc_api_version,
        hmc_features):
    """
    Return the names of the metric-based and resource-based metric groups that
    are enabled for export, as defined in the exporter config file.

    Returns:

      tuple(metric_mg_names, resource_mg_names): Names of the metric groups
      that are enabled for export, with:
      - metric_mg_names (list of str): Metric-based metric groups
      - resource_mg_names (list of str): Resource-based metric groups
    """
    config_mg_dict = config_dict["metric_groups"]
    metric_mg_names = []
    resource_mg_names = []
    for metric_group in yaml_metric_groups:
        mg_dict = yaml_metric_groups[metric_group]
        mg_type = mg_dict["type"]
        # Not all metric groups may be specified:
        config_mg_item = config_mg_dict.get(metric_group, {})
        export = config_mg_item.get("export", False)
        # if is optional in the metrics schema:
        if export and "if" in mg_dict:
            export = eval_condition(
                f"metric group {metric_group!r}",
                mg_dict["if"], hmc_version, hmc_api_version, hmc_features,
                None, None, None)
        if export:
            if mg_type == 'metric':
                metric_mg_names.append(metric_group)
            else:
                assert mg_type == 'resource'  # ensured by enum
                resource_mg_names.append(metric_group)
    return metric_mg_names, resource_mg_names


def create_metrics_context(client, metric_mg_names):
    """
    Creating a context is mandatory for reading metrics from the Z HMC.
    Takes the session, the metric_groups dictionary from the metrics YAML file
    for fetch/do not fetch information, and the name of the YAML file for error
    output.

    If the list of metric groups is empty, no metrics context is created, and
    None is returned. This is because when an empty list of metric groups is
    specified to the HMC, it assumes a default set of metric groups.

    Parameters:
      client (zhmcclient.Client): Client for communicating with the HMC
      metric_mg_names (list of str): Names of metric-based metric groups.
        May be an empty list.

    Returns:
      context (zhmcclient.MetricContext): The metric context, or None if the
        List of metric groups was empty.

    Raises:
      zhmccclient exceptions
    """
    if not metric_mg_names:
        logprint(logging.INFO, PRINT_V,
                 "No metrics context needs to be created on the HMC")
        return None

    logprint(logging.INFO, PRINT_V,
             "Creating a metrics context on the HMC")
    context = client.metrics_contexts.create(
        {"anticipated-frequency-seconds": 15,
         "metric-groups": metric_mg_names})
    return context


def cleanup(session, context, resources, coll):
    """
    Clean up:
    - cleanup the fetch thread
    - delete the metric context
    - disable auto-update on resources
    - logoff from the HMC session
    """

    try:

        if coll:
            logprint(logging.INFO, PRINT_ALWAYS,
                     "Cleaning up thread for fetching properties in background "
                     "(may take some time)")
            coll.cleanup_fetch_thread()

        if context:
            logprint(logging.INFO, PRINT_ALWAYS,
                     "Cleaning up metrics context on HMC")
            try:
                context.delete()
            except zhmcclient.HTTPError as exc:
                if exc.http_status == 404 and exc.reason == 1:
                    # The metrics context does not exist anymore
                    pass
                elif exc.http_status == 403:
                    # The session does not exist anymore
                    pass

        if resources:
            logprint(logging.INFO, PRINT_ALWAYS,
                     "Cleaning up notification subscription on HMC")
            for res_list in resources.values():
                for res in res_list:
                    try:
                        res.disable_auto_update()
                    except zhmcclient.HTTPError as exc:
                        if exc.http_status == 403:
                            # The session does not exist anymore
                            pass
        if session:
            logprint(logging.INFO, PRINT_ALWAYS,
                     "Closing session with HMC")
            try:
                session.logoff()
            except zhmcclient.HTTPError as exc:
                if exc.http_status == 403:
                    # The session does not exist anymore
                    pass

    except zhmcclient.Error as exc:
        logprint(logging.ERROR, PRINT_ALWAYS,
                 f"Error when cleaning up: {exc}")


def retrieve_metrics(context):
    """
    Retrieve metrics from the Z HMC.

    Parameters:
      context (zhmcclient.MetricsContext): HMC metric context. Must not be None.

    Returns:
      zhmcclient.MetricsResponse: The metrics.

    Raises:
      zhmccclient exceptions
    """
    retrieved_metrics = context.get_metrics()
    metrics_object = zhmcclient.MetricsResponse(context, retrieved_metrics)
    return metrics_object


def expand_global_label_value(
        env, label_name, item_value, hmc_info):
    """
    Expand a Jinja2 expression on a label value, for a global (extra) label.
    """
    try:
        func = env.compile_expression(item_value)
    except jinja2.TemplateSyntaxError as exc:
        logprint(logging.WARNING, PRINT_ALWAYS,
                 f"Not adding global label '{label_name}' due to syntax error "
                 f"in the Jinja2 expression for the label value: {exc}")
        return None
    try:
        value = func(hmc_info=hmc_info)
    # pylint: disable=broad-exception-caught,broad-except
    except Exception as exc:
        tb_str = traceback.format_tb(exc.__traceback__, limit=-1)[0]
        logprint(logging.WARNING, PRINT_ALWAYS,
                 f"Not adding global label '{label_name}' due to error when "
                 "rendering the Jinja2 expression for the label value: "
                 f"{exc.__class__.__name__}: {exc}\n{tb_str}")
        return None
    return str(value)


def expand_group_label_value(
        env, label_name, group_name, item_value, resource_obj,
        resource_cache, metric_values=None):
    """
    Expand a Jinja2 expression on a label value, for a metric group label.
    """

    def uri2resource_func(uri):
        return resource_cache.lookup(uri)

    def uris2resources_func(uris):
        return [resource_cache.lookup(uri) for uri in uris]

    def adapter_name_func(nic):
        # Get the original Nic object that has the dynamic attributes with the
        # adapter info
        nic_org = resource_cache.lookup(nic.uri)
        return nic_org.adapter_name

    def adapter_port_func(nic):
        # Get the original Nic object that has the dynamic attributes with the
        # adapter info
        nic_org = resource_cache.lookup(nic.uri)
        return str(nic_org.port_index)

    try:
        func = env.compile_expression(item_value)
    except jinja2.TemplateSyntaxError as exc:
        logprint(logging.WARNING, PRINT_ALWAYS,
                 f"Not adding label '{label_name}' to metrics of metric "
                 f"group '{group_name}' due to syntax error in the Jinja2 "
                 f"expression for the label value: {exc}")
        return None
    try:
        value = func(
            resource_obj=resource_obj,
            metric_values=metric_values,
            uri2resource=uri2resource_func,
            uris2resources=uris2resources_func,
            adapter_name=adapter_name_func,
            adapter_port=adapter_port_func)
    # pylint: disable=broad-exception-caught,broad-except
    except Exception as exc:
        tb_str = traceback.format_tb(exc.__traceback__, limit=-1)[0]
        logprint(logging.WARNING, PRINT_ALWAYS,
                 f"Not adding label '{label_name}' on the metrics of metric "
                 f"group '{group_name}' due to error when rendering the Jinja2 "
                 "expression for the label value: "
                 f"{exc.__class__.__name__}: {exc}\n{tb_str}")
        return None
    return str(value)


def expand_metric_label_value(
        env, label_name, metric_exporter_name, item_value, resource_obj,
        resource_cache, metric_values=None):
    """
    Expand a Jinja2 expression on a label value, for a metric label.
    """

    def uri2resource_func(uri):
        return resource_cache.lookup(uri)

    def uris2resources_func(uris):
        return [resource_cache.lookup(uri) for uri in uris]

    def adapter_name_func(nic):
        # Get the original Nic object that has the dynamic attributes with the
        # adapter info
        nic_org = resource_cache.lookup(nic.uri)
        return nic_org.adapter_name

    def adapter_port_func(nic):
        # Get the original Nic object that has the dynamic attributes with the
        # adapter info
        nic_org = resource_cache.lookup(nic.uri)
        return str(nic_org.port_index)

    try:
        func = env.compile_expression(item_value)
    except jinja2.TemplateSyntaxError as exc:
        logprint(logging.WARNING, PRINT_ALWAYS,
                 f"Not adding label '{label_name}' on Prometheus metric "
                 f"'{metric_exporter_name}' due to syntax error in Jinja2 "
                 f"expression {item_value!r} for the label value: {exc}")
        return None
    try:
        value = func(
            resource_obj=resource_obj,
            metric_values=metric_values,
            uri2resource=uri2resource_func,
            uris2resources=uris2resources_func,
            adapter_name=adapter_name_func,
            adapter_port=adapter_port_func)
    # pylint: disable=broad-exception-caught,broad-except
    except Exception as exc:
        tb_str = traceback.format_tb(exc.__traceback__, limit=-1)[0]
        logprint(logging.WARNING, PRINT_ALWAYS,
                 f"Not adding label '{label_name}' on Prometheus metric "
                 f"'{metric_exporter_name}' due to error when rendering "
                 f"Jinja2 expression {item_value!r} for the label value: "
                 f"{exc.__class__.__name__}: {exc}\n{tb_str}")
        return None
    return str(value)


def build_family_objects(
        resource_cache, metrics_object, yaml_metric_groups, yaml_metrics,
        extra_labels, hmc_version, hmc_api_version, hmc_features,
        se_versions_by_cpc, se_features_by_cpc):
    """
    Go through all retrieved metrics and build the Prometheus Family objects.

    Returns a dictionary of Prometheus Family objects with the following
    structure:

      family_name:
        GaugeMetricFamily object
    """
    env = jinja2.Environment(autoescape=True)

    family_objects = {}
    for metric_group_value in metrics_object.metric_group_values:
        metric_group = metric_group_value.name

        try:
            yaml_metric_group = yaml_metric_groups[metric_group]
        except KeyError:
            warnings.warn(
                f"The HMC supports a new metric group {metric_group!r} that is "
                "not yet supported by this version of the exporter. Please "
                "open an exporter issue to get the new metric group supported.")
            continue  # Skip this metric group

        for object_value in metric_group_value.object_values:

            try:
                resource = resource_cache.lookup(object_value.resource_uri)
            except zhmcclient.NotFound:
                # Some details have already been logged & printed
                warnings.warn(
                    f"The HMC metric group {metric_group!r} contains a "
                    f"resource with URI '{object_value.resource_uri}' "
                    "that is not found on the HMC. Please open an exporter "
                    "issue for that.")
                continue  # Skip this metric

            # The metric service does not support filtering by CPC, so we have
            # to filter here.
            if not resource_cache.is_for_target_cpc(resource):
                continue  # Skip this metric

            metric_values = object_value.metrics

            cpc = resource_cache.cpc_from_resource(resource)
            if cpc:
                # This resource has a CPC (itself, parent, associated)
                se_version = se_versions_by_cpc[cpc.name]
                se_features = se_features_by_cpc[cpc.name]
            else:
                # This resource does not have a CPC. This should not happen
                # for the resource classes supported right now.
                se_version = None
                se_features = []

            # Calculate the resource labels at the metric group level:
            mg_labels = dict(extra_labels)
            # labels is optional in the metrics schema:
            default_labels = [dict(name='resource', value='resource_obj.name')]
            yaml_labels = yaml_metric_group.get('labels', default_labels)
            for item in yaml_labels:
                # name, value are required in the metrics schema:
                label_name = item['name']
                item_value = item['value']
                label_value = expand_group_label_value(
                    env, label_name, metric_group, item_value, resource,
                    resource_cache, metric_values)
                if label_value is not None:
                    mg_labels[label_name] = label_value

            for metric in metric_values:

                try:
                    yaml_metric = yaml_metrics[metric_group][metric]
                except KeyError:
                    warnings.warn(
                        f"The HMC supports a new metric {metric!r} in "
                        f"metric group {metric_group!r} that is not yet "
                        "supported by this version of the exporter. Please "
                        "open an exporter issue to get the new metric "
                        "supported.")
                    continue  # Skip this metric

                metric_value = metric_values[metric]

                # Skip metrics with the special value -1 (which indicates that
                # the resource does not exist)
                if metric_value == -1:
                    continue

                exporter_name = yaml_metric["exporter_name"]

                # Skip metrics that are defined to be ignored
                # exporter_name is required in the metrics schema:
                if not exporter_name:
                    continue

                # Skip conditional metrics that their condition not met
                if_expr = yaml_metric.get("if", None)
                if if_expr and not eval_condition(
                        f"Prometheus metric {exporter_name!r}",
                        if_expr, hmc_version, hmc_api_version, hmc_features,
                        se_version, se_features, resource):
                    continue

                # Transform HMC percentages (value 100 means 100% = 1) to
                # Prometheus values (value 1 means 100% = 1)
                # percent is optional in the metrics schema:
                if yaml_metric.get("percent", False):
                    metric_value /= 100

                # Calculate the resource labels at the metric level:
                labels = dict(mg_labels)
                # labels is optional in the metrics schema:
                yaml_labels = yaml_metric.get('labels', [])
                for item in yaml_labels:
                    # name, value are required in the metrics schema:
                    label_name = item['name']
                    item_value = item['value']
                    label_value = expand_metric_label_value(
                        env, label_name, yaml_metric["exporter_name"],
                        item_value, resource, resource_cache, metric_values)
                    if label_value is not None:
                        labels[label_name] = label_value

                # Create a Family object, if needed
                # prefix,exporter_name are required in the metrics schema:
                family_name = "zhmc_{}_{}".format(
                    yaml_metric_group["prefix"],
                    yaml_metric["exporter_name"])
                try:
                    family_object = family_objects[family_name]
                except KeyError:
                    # exporter_desc is required in the metrics schema:
                    metric_type = yaml_metric.get("metric_type", "gauge")
                    if metric_type == "gauge":
                        family_object = GaugeMetricFamily(
                            family_name,
                            yaml_metric["exporter_desc"],
                            labels=list(labels.keys()))
                    else:
                        assert metric_type == "counter"  # ensured by schema
                        family_object = CounterMetricFamily(
                            family_name,
                            yaml_metric["exporter_desc"],
                            labels=list(labels.keys()))
                    family_objects[family_name] = family_object

                # Add the metric value to the Family object
                family_object.add_metric(list(labels.values()), metric_value)

    return family_objects


def build_family_objects_res(
        resource_cache, yaml_metric_groups, yaml_metrics, extra_labels,
        hmc_version, hmc_api_version, hmc_features, se_versions_by_cpc,
        se_features_by_cpc):
    """
    Go through all auto-updated resources and build the Prometheus Family
    objects for them.

    Returns a dictionary of Prometheus Family objects with the following
    structure:

      family_name:
        GaugeMetricFamily object
    """
    env = jinja2.Environment(autoescape=True)

    family_objects = {}
    for metric_group, res_list in \
            resource_cache.resource_based_resources.items():

        ceased_res_indexes = []  # Indexes into res_list

        yaml_metric_group = yaml_metric_groups[metric_group]
        for i, resource in enumerate(res_list):

            if resource.ceased_existence:
                try:
                    res_str = resource.name
                except zhmcclient.CeasedExistence:
                    # For attribute 'name', the exception is only raised when
                    # the name is not yet known locally.
                    res_str = f"with URI {resource.uri}"
                logprint(logging.INFO, PRINT_VV,
                         "Resource no longer exists on HMC: "
                         f"{resource.manager.class_name} {res_str}")

                # Remember the resource to be removed
                ceased_res_indexes.append(i)

                continue

            cpc = resource_cache.cpc_from_resource(resource)
            if cpc:
                # This resource has a CPC (itself, parent, associated)
                se_version = se_versions_by_cpc[cpc.name]
                se_features = se_features_by_cpc[cpc.name]
            else:
                # This resource does not have a CPC. This should not happen
                # for the resource classes supported right now.
                se_version = None
                se_features = []

            # Calculate the resource labels at the metric group level:
            mg_labels = dict(extra_labels)
            # labels is optional in the metrics schema:
            default_labels = [dict(name='resource', value='resource_obj.name')]
            yaml_labels = yaml_metric_group.get('labels', default_labels)
            for item in yaml_labels:
                # name, value are required in the metrics schema:
                label_name = item['name']
                item_value = item['value']
                label_value = expand_group_label_value(
                    env, label_name, metric_group, item_value, resource,
                    resource_cache)
                if label_value is not None:
                    mg_labels[label_name] = label_value

            yaml_mg = yaml_metrics[metric_group]
            if isinstance(yaml_mg, dict):
                yaml_mg_iter = yaml_mg.items()
            else:
                yaml_mg_iter = yaml_mg
            for item in yaml_mg_iter:
                if isinstance(yaml_mg, dict):
                    prop_name, yaml_metric = item
                else:
                    yaml_metric = item
                    prop_name = yaml_metric.get('property_name', None)

                # exporter_name is required in the metrics schema
                exporter_name = yaml_metric["exporter_name"]

                # Skip metrics that are defined to be ignored
                if not exporter_name:
                    continue

                # Skip conditional metrics that their condition not met
                if_expr = yaml_metric.get("if", None)
                if if_expr and not eval_condition(
                        f"Prometheus metric {exporter_name!r}",
                        if_expr, hmc_version, hmc_api_version, hmc_features,
                        se_version, se_features, resource):
                    continue

                if prop_name:
                    try:
                        metric_value = resource.properties[prop_name]
                    except KeyError:
                        # Skip this resource metric, because the HMC/SE does
                        # not support the corresponding property. This happens
                        # for some condition expressionss that cannot properly
                        # reflect the exact condition that would be needed.
                        if cpc:
                            res_str = f" for CPC '{cpc.name}'"
                        else:
                            res_str = ""
                        warnings.warn(
                            f"Skipping Prometheus metric '{exporter_name}' in "
                            f"resource metric group '{metric_group}' in the "
                            f"metric definition file, because its resource "
                            f"property '{prop_name}' is not returned by the "
                            f"HMC{res_str}")
                        continue
                else:
                    prop_expr = yaml_metric.get('properties_expression', None)
                    if not prop_expr:
                        new_exc = InvalidMetricDefinitionFile(
                            f"Exporter name '{exporter_name}' in the "
                            "metric definition file has neither "
                            "'property_name' nor 'properties_expression'")
                        new_exc.__cause__ = None  # pylint: disable=invalid-name
                        raise new_exc

                    try:
                        func = env.compile_expression(
                            prop_expr, undefined_to_none=False)
                    except jinja2.exceptions.TemplateError as exc:
                        new_exc = InvalidMetricDefinitionFile(
                            "Error compiling properties expression "
                            f"{prop_expr!r} defined for exporter name "
                            f"'{exporter_name}' in the metric definition file: "
                            f"{exc.__class__.__name__}: {exc}")
                        new_exc.__cause__ = None  # pylint: disable=invalid-name
                        raise new_exc

                    try:
                        metric_value = func(properties=resource.properties)
                    # pylint: disable=broad-exception-caught,broad-except
                    except Exception as exc:
                        # Typical exceptions:
                        # - jinja2.exceptions.UndefinedError, e.g. for missing
                        #   HMC resource properties
                        # - TypeError
                        tb_str = traceback.format_tb(
                            exc.__traceback__, limit=-1)[0]
                        logprint(
                            logging.WARNING, PRINT_ALWAYS,
                            "Not providing Prometheus metric "
                            f"{exporter_name!r} due to error evaluating its "
                            f"properties expression {prop_expr!r}: "
                            f"{exc.__class__.__name__}: {exc}\n{tb_str}")
                        continue

                # Skip resource properties that have a null value. An example
                # are some LPAR/partition properties that are null when the
                # partition is not active. Prometheus cannot represent null
                # values (It can represent the NaN float value but that would
                # not really be the right choice).
                if metric_value is None:
                    continue

                # Skip metrics that are defined to be ignored.
                # exporter_name is required in the metrics schema.
                if not yaml_metric["exporter_name"]:
                    continue

                exporter_name = yaml_metric["exporter_name"]

                # Skip conditional metrics that their condition not met
                if_expr = yaml_metric.get("if", None)
                if if_expr and not eval_condition(
                        f"Prometheus metric {exporter_name!r}",
                        if_expr, hmc_version, hmc_api_version, hmc_features,
                        se_version, se_features, resource):
                    continue

                # Transform the HMC value using the valuemap, if defined:
                valuemap = yaml_metric.get('valuemap', None)
                if valuemap:
                    try:
                        metric_value = valuemap[metric_value]
                    except KeyError:
                        res_str = resource_str(resource)
                        warnings.warn(
                            f"Skipping property '{prop_name}' of resource "
                            f"metric group '{metric_group}' in the "
                            "metric definition file, because its valuemap does "
                            f"not define a mapping for value {metric_value!r} "
                            f"returned for {res_str}")
                        continue

                # Transform HMC percentages (value 100 means 100% = 1) to
                # Prometheus values (value 1 means 100% = 1)
                # percent is optional in the metrics schema:
                if yaml_metric.get("percent", False):
                    metric_value /= 100

                # Calculate the resource labels at the metric level:
                labels = dict(mg_labels)
                # labels is optional in the metrics schema:
                yaml_labels = yaml_metric.get('labels', [])
                for item in yaml_labels:  # pylint: disable=redefined-outer-name
                    # name, value are required in the metrics schema:
                    label_name = item['name']
                    item_value = item['value']
                    label_value = expand_metric_label_value(
                        env, label_name, exporter_name, item_value, resource,
                        resource_cache)
                    if label_value is not None:
                        labels[label_name] = label_value

                # Create a Family object, if needed
                # prefix,exporter_name are required in the metrics schema:
                family_name = "zhmc_{}_{}".format(
                    yaml_metric_group["prefix"],
                    yaml_metric["exporter_name"])
                try:
                    family_object = family_objects[family_name]
                except KeyError:
                    # exporter_desc is required in the metrics schema:
                    metric_type = yaml_metric.get("metric_type", "gauge")
                    if metric_type == "gauge":
                        family_object = GaugeMetricFamily(
                            family_name,
                            yaml_metric["exporter_desc"],
                            labels=list(labels.keys()))
                    else:
                        assert metric_type == "counter"  # ensured by schema
                        family_object = CounterMetricFamily(
                            family_name,
                            yaml_metric["exporter_desc"],
                            labels=list(labels.keys()))
                    family_objects[family_name] = family_object

                # Add the metric value to the Family object
                family_object.add_metric(list(labels.values()), metric_value)

        # Remove the ceased resources from our data structures.
        # Note: Deleting items from a list by index requires going backwards.
        for i in reversed(ceased_res_indexes):

            res_uri = res_list[i].uri

            # Remove the resource from the resource list in 'resources' so it
            # no longer shows up in the exported Prometheus data.
            del res_list[i]

            # Remove the resource from the resource cache. This does not
            # influence what is shown in Prometheus data, but it is simply
            # a cleanup.
            if resource_cache:
                resource_cache.remove(res_uri)

    return family_objects


class ZHMCUsageCollector():
    # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """Collects the usage for exporting."""

    def __init__(self, config_dict, client, context, yaml_metric_groups,
                 yaml_metrics, yaml_fetch_properties, extra_labels,
                 all_cpc_list, target_cpc_list, metrics_filename,
                 config_filename, resource_cache, hmc_version, hmc_api_version,
                 hmc_features, se_versions_by_cpc, se_features_by_cpc):
        self.config_dict = config_dict
        self.client = client
        self.context = context
        self.yaml_metric_groups = yaml_metric_groups
        self.yaml_metrics = yaml_metrics
        self.yaml_fetch_properties = yaml_fetch_properties
        self.extra_labels = extra_labels
        self.all_cpc_list = all_cpc_list
        self.target_cpc_list = target_cpc_list
        self.metrics_filename = metrics_filename
        self.config_filename = config_filename
        self.resource_cache = resource_cache
        self.hmc_version = hmc_version
        self.hmc_api_version = hmc_api_version
        self.hmc_features = hmc_features
        self.se_versions_by_cpc = se_versions_by_cpc
        self.se_features_by_cpc = se_features_by_cpc
        self.fetch_thread = None
        self.fetch_event = None
        self.last_export_dt = None
        self.export_interval = None
        self.exported_metric_mg_names, _ = exported_metric_groups(
            config_dict, yaml_metric_groups, hmc_version, hmc_api_version,
            hmc_features)

    def collect(self):
        """
        Yield the metrics for exporting.
        Uses the context, the metric groups and the metrics from the YAML file,
        and the name of the YAML file for error output.

        Retries indefinitely in case of connection problems with the HMC or
        in case of HTTP errors. HTTP 404.1 is automatically handled by
        refreshing the metrics context.

        Raises exception in case of authentication errors or other errors.
        """
        logprint(logging.INFO, None,
                 "Collecting metrics")

        start_dt = datetime.now()

        family_objects = {}

        if self.context:
            with zhmc_exceptions(self.client.session, self.config_filename):

                while True:
                    logprint(logging.DEBUG, None,
                             "Fetching metrics from HMC")
                    try:
                        metrics_object = retrieve_metrics(self.context)
                    except zhmcclient.HTTPError as exc:
                        if exc.http_status == 400 and exc.reason in (13, 45):
                            # 400.13: Logon: Max sessions reached for user
                            # 400.45: Logon: Password expired
                            logprint(logging.ERROR, PRINT_ALWAYS,
                                     "Abandoning after HTTP status "
                                     f"{exc.http_status}.{exc.reason}: {exc}")
                            raise
                        if exc.http_status == 404 and exc.reason == 1:
                            logprint(logging.WARNING, PRINT_ALWAYS,
                                     "Recreating the metrics context after "
                                     "HTTP status "
                                     f"{exc.http_status}.{exc.reason}")
                            self.context = create_metrics_context(
                                self.client, self.exported_metric_mg_names)
                            continue
                        logprint(logging.WARNING, PRINT_ALWAYS,
                                 "Retrying after HTTP status "
                                 f"{exc.http_status}.{exc.reason}: {exc}")
                        time.sleep(RETRY_SLEEP_TIME)
                        continue
                    except zhmcclient.ConnectionError as exc:
                        logprint(logging.WARNING, PRINT_ALWAYS,
                                 f"Retrying after connection error: {exc}")
                        time.sleep(RETRY_SLEEP_TIME)
                        continue
                    except zhmcclient.ServerAuthError as exc:
                        logprint(logging.ERROR, PRINT_ALWAYS,
                                 "Abandoning after server authentication "
                                 f"error: {exc}")
                        raise
                    except zhmcclient.ClientAuthError as exc:
                        logprint(logging.ERROR, PRINT_ALWAYS,
                                 "Abandoning after client authentication "
                                 f"error: {exc}")
                        raise
                    # pylint: disable=broad-exception-caught,broad-except
                    except Exception as exc:
                        tb_str = traceback.format_tb(
                            exc.__traceback__, limit=-1)[0]
                        logprint(logging.ERROR, PRINT_ALWAYS,
                                 "Abandoning after exception "
                                 f"{exc.__class__.__name__}: {exc}\n{tb_str}")
                        raise
                    break

            logprint(logging.DEBUG, None,
                     "Building family objects for HMC metrics")
            family_objects.update(build_family_objects(
                self.resource_cache, metrics_object, self.yaml_metric_groups,
                self.yaml_metrics, self.extra_labels, self.hmc_version,
                self.hmc_api_version, self.hmc_features,
                self.se_versions_by_cpc, self.se_features_by_cpc))

        logprint(logging.DEBUG, None,
                 "Building family objects for resource metrics")
        family_objects.update(build_family_objects_res(
            self.resource_cache, self.yaml_metric_groups, self.yaml_metrics,
            self.extra_labels, self.hmc_version, self.hmc_api_version,
            self.hmc_features, self.se_versions_by_cpc,
            self.se_features_by_cpc))

        logprint(logging.DEBUG, None,
                 "Returning family objects")
        # Yield all family objects
        yield from family_objects.values()

        end_dt = datetime.now()
        duration = (end_dt - start_dt).total_seconds()
        if self.last_export_dt:
            self.export_interval = \
                (end_dt - self.last_export_dt).total_seconds()
        self.last_export_dt = end_dt
        interval_str = f"{self.export_interval:.1f} sec" if \
            self.export_interval else "None"
        logprint(logging.INFO, None,
                 f"Done collecting metrics after {duration:.1f} sec "
                 f"(export interval: {interval_str})")

    def run_fetch_thread(self, session):
        """
        Function that runs as the property fetch thread.
        """
        assert isinstance(self, ZHMCUsageCollector)
        assert isinstance(session, zhmcclient.Session)
        client = zhmcclient.Client(session)
        console = client.consoles.console
        sleep_time = INITIAL_FETCH_SLEEP_TIME

        while True:

            # Sleep, but wake up when stop event is set
            self.fetch_event.wait(timeout=sleep_time)

            # Check for thread to stop
            if self.fetch_event.is_set():
                break

            # Build the list of properties to be fetched.
            # We do that every time, in order to handle new HMC features after
            # an online upgrade.
            cpc_props = []  # HMC property names of CPC to be fetched
            lpar_props = []  # HMC property names of LPAR to be fetched
            for fetch_class, fetch_item in self.yaml_fetch_properties.items():
                for prop_item in fetch_item['properties']:
                    prop_name = prop_item["property_name"]

                    # Skip properties where fetch condition is not met
                    if_expr = prop_item.get("if", None)
                    if if_expr and not eval_condition(
                            f"metric property {prop_name!r}",
                            if_expr, self.hmc_version, self.hmc_api_version,
                            self.hmc_features, None, None, None):
                        continue

                    if fetch_class == 'cpc':
                        cpc_props.append(prop_name)
                    elif fetch_class == 'logical-partition':
                        lpar_props.append(prop_name)
                    else:
                        logprint(logging.ERROR, PRINT_ALWAYS,
                                 f"Unknown resource type {fetch_class!r} when "
                                 "fetching properties in background")

            # Fetch the properties.
            # The zhmcclient methods used for that are supported for all HMC
            # versions, but they run faster starting with HMC API version 4.10
            # (2.16.0 GA 1.5).

            logprint(logging.INFO, None,
                     "Fetching properties in background")
            start_dt = datetime.now()

            updated_resources = {}  # Resource object by URI

            if self.resource_cache.is_auto_update('logical-partition'):
                cpc_names = [cpc.name for cpc in self.target_cpc_list]
                filter_args = {
                    # cpc-name supports regex matching
                    "cpc-name": f"{'|'.join(cpc_names)}"
                }
                lpars = console.list_permitted_lpars(
                    filter_args=filter_args,
                    additional_properties=lpar_props)
                for lpar in lpars:
                    updated_resources[lpar.uri] = lpar

            if self.resource_cache.is_auto_update('cpc'):
                for cpc in self.target_cpc_list:
                    cpc.pull_properties(cpc_props)
                    updated_resources[cpc.uri] = cpc

            end_dt = datetime.now()
            duration = (end_dt - start_dt).total_seconds()
            logprint(logging.INFO, None,
                     "Done fetching properties in background after "
                     f"{duration:.1f} sec")

            # Adjust the fetch sleep time based on the exporter interval.
            # This assumes that the export to Prometheus happens on a fairly
            # regular basis.
            if self.export_interval:
                old_sleep_time = sleep_time
                if duration + sleep_time < \
                        self.export_interval - FETCH_HYSTERESIS:
                    sleep_time = int(self.export_interval - duration)
                elif duration + sleep_time > \
                        self.export_interval + FETCH_HYSTERESIS:
                    sleep_time = int(self.export_interval - duration)
                sleep_time = max(sleep_time, MIN_FETCH_SLEEP_TIME)
                sleep_time = min(sleep_time, MAX_FETCH_SLEEP_TIME)
                if sleep_time > old_sleep_time:
                    direction_str = "Increasing"
                elif sleep_time < old_sleep_time:
                    direction_str = "Decreasing"
                else:
                    direction_str = None
                if direction_str:
                    logprint(logging.INFO, PRINT_ALWAYS,
                             f"{direction_str} sleep time for fetching "
                             f"properties in background from {old_sleep_time} "
                             f"sec to {sleep_time} sec to adjust to export "
                             f"interval of {self.export_interval:.1f} sec")

            # Update properties of our local resource objects from result
            for uri, updated_res in updated_resources.items():
                res = self.resource_cache.lookup(uri)
                res.update_properties_local(updated_res.properties)

    def start_fetch_thread(self, session):
        """
        Start the property fetch thread.
        """
        self.fetch_event = threading.Event()
        self.fetch_thread = threading.Thread(
            name='FetchThread',
            target=self.run_fetch_thread,
            kwargs=dict(session=session))
        self.fetch_thread.start()

    def cleanup_fetch_thread(self):
        """
        Stop and clean up the property fetch thread.
        """
        if self.fetch_thread:
            self.fetch_event.set()
            self.fetch_thread.join()


def main():
    """Puts the exporter together."""

    # If the session and context keys are not created, their destruction
    # should not be attempted.
    session = None
    context = None
    resources = None
    coll = None  # For exceptions that happen before it is set

    try:
        args = parse_args(sys.argv[1:])
        config_filename = args.c
        if args.version:
            print_version()
            sys.exit(0)
        if args.help_config:
            help_config()
            sys.exit(0)
        if args.upgrade_config:
            logprint(logging.INFO, PRINT_V,
                     f"Upgrading exporter config file: {config_filename}")
            upgrade_config_file(config_filename)
            sys.exit(0)

        setup_logging(args.log_dest, args.log_complevels, args.syslog_facility,
                      args.verbose)

        logprint(logging.INFO, None,
                 "---------------- "
                 "zhmc_prometheus_exporter started "
                 "----------------")

        logprint(logging.INFO, PRINT_ALWAYS,
                 f"zhmc_prometheus_exporter version: {__version__}")

        # pylint: disable=no-member
        logprint(logging.INFO, PRINT_ALWAYS,
                 f"zhmcclient version: {zhmcclient.__version__}")

        logprint(logging.INFO, PRINT_ALWAYS,
                 f"Verbosity level: {args.verbose}")

        logprint(logging.INFO, PRINT_V,
                 f"Parsing exporter config file: {config_filename}")
        config_dict = parse_config_file(config_filename)

        metrics_filename = os.path.join(
            os.path.dirname(__file__), 'data', 'metrics.yaml')

        logprint(logging.INFO, PRINT_V,
                 f"Parsing metric definition file: {metrics_filename}")
        yaml_metric_content = parse_yaml_file(
            metrics_filename, 'metric definition file', 'metrics_schema.yaml')
        # metric_groups and metrics are required in the metrics schema:
        yaml_metric_groups = yaml_metric_content['metric_groups']
        yaml_metrics = yaml_metric_content['metrics']
        yaml_fetch_properties = yaml_metric_content.get(
            'fetch_properties', None)

        # Check that the metric_groups and metrics items are consistent
        for mg in yaml_metrics:
            if mg not in yaml_metric_groups:
                new_exc = InvalidMetricDefinitionFile(
                    f"Metric group '{mg}' in the metric definition file "
                    "is defined in 'metrics' but not in 'metric_groups'")
                new_exc.__cause__ = None  # pylint: disable=invalid-name
                raise new_exc
        for mg in yaml_metric_groups:
            if mg not in yaml_metrics:
                new_exc = InvalidMetricDefinitionFile(
                    f"Metric group '{mg}' in the metric definition file "
                    "is defined in 'metric_groups' but not in 'metrics'")
                new_exc.__cause__ = None  # pylint: disable=invalid-name
                raise new_exc

        # Check that the correct format is used in the metrics section
        for mg, yaml_m in yaml_metrics.items():
            yaml_mg = yaml_metric_groups[mg]
            mg_type = yaml_mg.get('type', 'metric')
            if mg_type == 'metric' and not isinstance(yaml_m, dict):
                new_exc = InvalidMetricDefinitionFile(
                    f"Metrics for metric group '{mg}' of type 'metric' must "
                    "use the dictionary format in the metric definition file")
                new_exc.__cause__ = None  # pylint: disable=invalid-name
                raise new_exc

        # Unregister the default collectors (Python, Platform)
        if hasattr(REGISTRY, '_collector_to_names'):
            # pylint: disable=protected-access
            for coll_ in list(REGISTRY._collector_to_names.keys()):
                REGISTRY.unregister(coll_)

        logprint(logging.INFO, PRINT_V,
                 "Initial sleep time for fetching properties in background: "
                 f"{INITIAL_FETCH_SLEEP_TIME} sec")

        yaml_cpcs = config_dict.get("cpcs", None)
        if yaml_cpcs == []:
            raise ImproperExit(
                "The config file specified to export no CPCs.")

        env = jinja2.Environment(autoescape=True)

        session = create_session(config_dict, config_filename)
        client = zhmcclient.Client(session)
        console = client.consoles.console

        try:
            with zhmc_exceptions(session, config_filename):
                hmc_info = get_hmc_info(session)
                hmc_version = split_version(hmc_info['hmc-version'], 3)
                hmc_api_version = (hmc_info['api-major-version'],
                                   hmc_info['api-minor-version'])
                hmc_features = console.list_api_features()

                # Determine list of CPCs to export, as specified in 'cpcs'.
                # 'cpcs' is optional and defaults to all managed CPCs.
                all_cpc_list = client.cpcs.list()
                all_cpc_names = [cpc.name for cpc in all_cpc_list]
                if not all_cpc_list:
                    raise ImproperExit(
                        "This HMC does not manage any CPCs.")
                if yaml_cpcs is not None:
                    ne_cpc_names = [cn for cn in yaml_cpcs
                                    if cn not in all_cpc_names]
                    if ne_cpc_names:
                        raise ImproperExit(
                            "The config file specified non-existing CPCs: "
                            f"{', '.join(ne_cpc_names)} - existing CPCs "
                            f"are: {', '.join(all_cpc_names)}")
                target_cpc_list = [cpc for cpc in all_cpc_list
                                   if not yaml_cpcs or cpc.name in yaml_cpcs]
                target_cpc_names = [cpc.name for cpc in target_cpc_list]

                se_versions_by_cpc = {}
                se_features_by_cpc = {}
                for cpc in target_cpc_list:
                    cpc_name = cpc.name
                    se_versions_by_cpc[cpc_name] = split_version(
                        cpc.prop('se-version'), 3)
                    se_features_by_cpc[cpc_name] = cpc.list_api_features()

                logprint(logging.INFO, PRINT_V,
                         f"HMC version: {version_str(hmc_version)}")
                logprint(logging.INFO, PRINT_V,
                         f"HMC API version: {version_str(hmc_api_version)}")
                hmc_features_str = ', '.join(hmc_features) or 'None'
                logprint(logging.INFO, PRINT_V,
                         f"HMC features: {hmc_features_str}")

                for cpc in target_cpc_list:
                    cpc_name = cpc.name
                    se_version_str = version_str(se_versions_by_cpc[cpc_name])
                    logprint(logging.INFO, PRINT_V,
                             f"SE version of CPC {cpc_name}: {se_version_str}")
                for cpc in target_cpc_list:
                    cpc_name = cpc.name
                    se_features_str = ', '.join(se_features_by_cpc[cpc_name]) \
                        or 'None'
                    logprint(logging.INFO, PRINT_V,
                             f"SE features of CPC {cpc_name}: "
                             f"{se_features_str}")

                metric_mg_names, resource_mg_names = exported_metric_groups(
                    config_dict, yaml_metric_groups, hmc_version,
                    hmc_api_version, hmc_features)
                exported_mg_names = metric_mg_names + resource_mg_names

                logprint(logging.INFO, PRINT_V,
                         "Caching resources for CPCs: "
                         f"{', '.join(all_cpc_names)}")
                logprint(logging.INFO, PRINT_V,
                         "Exporting metrics for CPCs: "
                         f"{', '.join(target_cpc_names)}")
                logprint(logging.INFO, PRINT_V,
                         "Exporting metric-based metric groups: "
                         f"{', '.join(metric_mg_names)}")
                logprint(logging.INFO, PRINT_V,
                         "Exporting resource-based metric groups: "
                         f"{', '.join(resource_mg_names)}")

                context = create_metrics_context(client, metric_mg_names)

                resource_cache = ResourceCache(
                    client, all_cpc_list, target_cpc_list, yaml_metric_groups,
                    exported_mg_names, se_features_by_cpc)

                logprint(logging.INFO, PRINT_V,
                         "Setting up the resource cache (may take some time)")

                start_dt = datetime.now()
                resource_cache.setup()  # Takes time
                end_dt = datetime.now()
                duration = (end_dt - start_dt).total_seconds()
                num_res = resource_cache.num_resources()
                num_cpcs = len(all_cpc_list)
                logprint(logging.INFO, PRINT_V,
                         f"Setup of resource cache is complete with {num_res} "
                         f"resources on {num_cpcs} CPCs after "
                         f"{duration:.0f} sec")

                # print(f"Debug: auto_update={resource_cache._auto_update!r}")
                # print(f"Debug: resource_cache={resource_cache!r}")

        except (ConnectionError, AuthError, OtherError) as exc:
            raise ImproperExit(exc)

        # Calculate the resource labels at the global level
        # extra_labels is optional in the metrics schema:
        yaml_extra_labels = config_dict.get("extra_labels", [])
        extra_labels = {}
        for item in yaml_extra_labels:
            # name is required in the config schema:
            label_name = item['name']
            item_value = item['value']
            label_value = expand_global_label_value(
                env, label_name, item_value, hmc_info)
            if label_value is not None:
                extra_labels[label_name] = label_value

        extra_labels_str = ','.join(
            [f'{k}="{v}"' for k, v in extra_labels.items()])
        logprint(logging.INFO, PRINT_V,
                 f"Using extra labels: {extra_labels_str}")

        coll = ZHMCUsageCollector(
            config_dict, client, context, yaml_metric_groups, yaml_metrics,
            yaml_fetch_properties, extra_labels, all_cpc_list, target_cpc_list,
            metrics_filename, config_filename, resource_cache, hmc_version,
            hmc_api_version, hmc_features, se_versions_by_cpc,
            se_features_by_cpc)

        logprint(logging.INFO, PRINT_V,
                 "Registering the collector and performing first collection")
        start_dt = datetime.now()
        REGISTRY.register(coll)  # Performs a first collection
        end_dt = datetime.now()
        duration = (end_dt - start_dt).total_seconds()
        logprint(logging.INFO, PRINT_V,
                 f"First collection is complete after {duration:.0f} sec")

        # print(f"Debug: resource_cache={resource_cache!r}")

        # Get the Prometheus communication parameters
        prom_item = config_dict.get("prometheus", {})
        config_port = prom_item.get("port", None)
        server_cert_file = prom_item.get("server_cert_file", None)
        if server_cert_file:
            prometheus_client_supports_https = sys.version_info[0:2] >= (3, 8)
            if not prometheus_client_supports_https:
                raise ImproperExit(
                    "Use of https requires Python 3.8 or higher.")
            server_key_file = prom_item.get("server_key_file", None)
            if not server_key_file:
                raise ImproperExit(
                    "server_key_file not specified in exporter config file "
                    "when using https.")
            config_dir = os.path.dirname(config_filename)
            if not os.path.isabs(server_cert_file):
                server_cert_file = os.path.join(config_dir, server_cert_file)
            if not os.path.isabs(server_key_file):
                server_key_file = os.path.join(config_dir, server_key_file)
            ca_cert_file = prom_item.get("ca_cert_file", None)
            if ca_cert_file and not os.path.isabs(ca_cert_file):
                ca_cert_file = os.path.join(config_dir, ca_cert_file)
        else:  # http
            server_cert_file = None
            server_key_file = None
            ca_cert_file = None

        port = int(args.p or config_port or DEFAULT_PORT)

        if server_cert_file:
            logprint(logging.INFO, PRINT_V,
                     f"Starting the server with HTTPS on port {port}")
            logprint(logging.INFO, PRINT_V,
                     f"Server certificate file: {server_cert_file}")
            logprint(logging.INFO, PRINT_V,
                     f"Server private key file: {server_key_file}")
            if ca_cert_file:
                logprint(logging.INFO, PRINT_V,
                         "Mutual TLS: Enabled with CA certificates file: "
                         f"{ca_cert_file}")
            else:
                logprint(logging.INFO, PRINT_V,
                         "Mutual TLS: Disabled")
        else:
            logprint(logging.INFO, PRINT_V,
                     f"Starting the server with HTTP on port {port}")

        if server_cert_file:
            try:
                # pylint: disable=unexpected-keyword-arg
                start_http_server(
                    port=port,
                    certfile=server_cert_file,
                    keyfile=server_key_file,
                    client_cafile=ca_cert_file,
                    client_auth_required=(ca_cert_file is not None))
            # pylint: disable=broad-exception
            except Exception as exc:
                # We catch Exception for now in order to investigate the
                # issue that with ssl.SSLEOFError being raised occasionally.
                raise ImproperExit(
                    f"Cannot start HTTPS server: {exc.__class__.__name__}: "
                    f"{exc}")
        else:
            try:
                start_http_server(port=port)
            except OSError as exc:
                raise ImproperExit(
                    f"Cannot start HTTP server: {exc.__class__.__name__}: "
                    f"{exc}")

        fetch_rcs = []
        for rc in ('cpc', 'logical-partition'):
            if resource_cache.is_auto_update(rc):
                fetch_rcs.append(rc)
        logprint(logging.INFO, PRINT_V,
                 "Starting thread for fetching properties in background for "
                 f"resource classes: {','.join(fetch_rcs)}")
        coll.start_fetch_thread(session)

        logprint(logging.INFO, PRINT_ALWAYS,
                 f"Exporter is up and running on port {port}")
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                raise ProperExit
    except KeyboardInterrupt:
        logprint(logging.WARNING, PRINT_ALWAYS,
                 "Exporter interrupted before server start.")
        cleanup(session, context, resources, coll)
        exit_rc(1)
    except EarlyExit as exc:
        logprint(logging.ERROR, PRINT_ALWAYS,
                 f"Error: {exc}")
        exit_rc(1)
    except InvalidMetricDefinitionFile as exc:
        logprint(logging.ERROR, PRINT_ALWAYS,
                 f"Error: Invalid metric definition file: {exc}")
        cleanup(session, context, resources, coll)
        exit_rc(1)
    except ImproperExit as exc:
        logprint(logging.ERROR, PRINT_ALWAYS,
                 f"Error: {exc}")
        cleanup(session, context, resources, coll)
        exit_rc(1)
    except ProperExit:
        logprint(logging.WARNING, PRINT_ALWAYS,
                 "Exporter interrupted after server start.")
        cleanup(session, context, resources, coll)
        exit_rc(0)


def exit_rc(rc):
    """Exit the script"""
    logprint(logging.WARNING, None,
             "---------------- "
             "zhmc_prometheus_exporter terminated "
             "----------------")
    sys.exit(rc)


if __name__ == "__main__":
    main()
