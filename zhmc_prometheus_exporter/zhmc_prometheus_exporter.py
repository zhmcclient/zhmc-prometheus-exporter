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
import types
import platform
import re
import time
from datetime import datetime
import warnings
import logging
import logging.handlers
import traceback
import threading
from contextlib import contextmanager

import jinja2
import urllib3
from ruamel.yaml import YAML, YAMLError
import jsonschema
import zhmcclient

from .vendor.prometheus_client import start_http_server
from .vendor.prometheus_client.core import GaugeMetricFamily, \
    CounterMetricFamily, REGISTRY
from .vendor import prometheus_client_version
from ._version import __version__

__all__ = []

DEFAULT_CONFIG_FILE = '/etc/zhmc-prometheus-exporter/config.yaml'
DEFAULT_PORT = 9291

EXPORTER_LOGGER_NAME = 'zhmcexporter'

# Logger names by log component
LOGGER_NAMES = {
    'exporter': EXPORTER_LOGGER_NAME,
    'hmc': zhmcclient.HMC_LOGGER_NAME,
    'jms': zhmcclient.JMS_LOGGER_NAME,
}
VALID_LOG_COMPONENTS = list(LOGGER_NAMES.keys()) + ['all']

# Log levels by their CLI names
LOG_LEVELS = {
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'off': logging.NOTSET,
}
VALID_LOG_LEVELS = list(LOG_LEVELS.keys())

# Defaults for --log-comp option.
DEFAULT_LOG_LEVEL = 'warning'
DEFAULT_LOG_COMP = 'all=warning'

# Values for printing messages dependent on verbosity level in command line
PRINT_ALWAYS = 0
PRINT_V = 1
PRINT_VV = 2

VALID_LOG_DESTINATIONS = ['stderr', 'syslog', 'FILE']

# Syslog facilities
VALID_SYSLOG_FACILITIES = [
    'user', 'local0', 'local1', 'local2', 'local3', 'local4', 'local5',
    'local6', 'local7'
]
DEFAULT_SYSLOG_FACILITY = 'user'

# Values to use for the 'address' parameter when creating a SysLogHandler.
# Key: Operating system type, as returned by platform.system(). For CygWin,
# the returned value is 'CYGWIN_NT-6.1', which is special-cased to 'CYGWIN_NT'.
# Value: Value for the 'address' parameter.
SYSLOG_ADDRESS = {
    'Linux': '/dev/log',
    'Darwin': '/var/run/syslog',  # macOS / OS-X
    'Windows': ('localhost', 514),
    'CYGWIN_NT': '/dev/log',  # Requires syslog-ng pkg
    'other': ('localhost', 514),  # used if no key matches
}

# Sleep time and hysteresis in property fetch thread
INITIAL_FETCH_SLEEP_TIME = 30
MIN_FETCH_SLEEP_TIME = 30
MAX_FETCH_SLEEP_TIME = 3600
FETCH_HYSTERESIS = 10

# Sleep time in seconds when retrying metrics retrieval
RETRY_SLEEP_TIME = 10

# Retry / timeout configuration for zhmcclient (used at the socket level)
RETRY_TIMEOUT_CONFIG = zhmcclient.RetryTimeoutConfig(
    connect_timeout=10,
    connect_retries=2,
    read_timeout=300,
    read_retries=2,
    max_redirects=zhmcclient.DEFAULT_MAX_REDIRECTS,
    operation_timeout=zhmcclient.DEFAULT_OPERATION_TIMEOUT,
    status_timeout=zhmcclient.DEFAULT_STATUS_TIMEOUT,
    name_uri_cache_timetolive=zhmcclient.DEFAULT_NAME_URI_CACHE_TIMETOLIVE,
)


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


class InvalidMetricDefinitionFile(ImproperExit):
    """Terminating because of invalid metric definition file"""
    pass


class EarlyExit(Exception):
    """Terminating before the server was started"""
    pass


@contextmanager
def zhmc_exceptions(session, config_filename):
    # pylint: disable=invalid-name
    """
    Context manager that handles zhmcclient exceptions by raising the
    appropriate exporter exceptions.

    Example::

        with zhmc_exceptions(session, config_filename):
            client = zhmcclient.Client(session)
            version_info = client.version_info()
    """
    try:
        yield
    except zhmcclient.ConnectionError as exc:
        new_exc = ConnectionError(
            f"Connection error using IP address {session.host} defined in "
            f"exporter config file {config_filename}: {exc}")
        new_exc.__cause__ = None
        raise new_exc  # ConnectionError
    except zhmcclient.ClientAuthError as exc:
        new_exc = AuthError(
            f"Client authentication error for the HMC at {session.host} using "
            f"userid '{session.userid}' defined in exporter config file "
            f"{config_filename}: {exc}")
        new_exc.__cause__ = None
        raise new_exc  # AuthError
    except zhmcclient.ServerAuthError as exc:
        http_exc = exc.details  # zhmcclient.HTTPError
        new_exc = AuthError(
            f"Authentication error returned from the HMC at {session.host} "
            f"using userid '{session.userid}' defined in exporter config file "
            f"{config_filename}: {exc} "
            f"(HMC operation {http_exc.request_method} {http_exc.request_uri}, "
            f"HTTP status {http_exc.http_status}.{http_exc.reason})")
        new_exc.__cause__ = None
        raise new_exc  # AuthError
    except OSError as exc:
        new_exc = OtherError(str(exc))
        new_exc.__cause__ = None
        raise new_exc  # OtherError
    except zhmcclient.Error as exc:
        new_exc = OtherError(
            f"Error returned from HMC at {session.host}: {exc}")
        new_exc.__cause__ = None
        raise new_exc  # OtherError


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


# Metrics context creation & deletion and retrieval derived from
# github.com/zhmcclient/python-zhmcclient/examples/metrics.py
def create_session(config_dict, config_filename):
    """
    To create a context, a session must be created first.

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

    session = zhmcclient.Session(hmc_dict["host"],
                                 hmc_dict["userid"],
                                 hmc_dict["password"],
                                 verify_cert=verify_cert,
                                 retry_timeout_config=RETRY_TIMEOUT_CONFIG)
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


def create_metrics_context(
        session, config_dict, yaml_metric_groups, hmc_version,
        hmc_api_version, hmc_features):
    """
    Creating a context is mandatory for reading metrics from the Z HMC.
    Takes the session, the metric_groups dictionary from the metrics YAML file
    for fetch/do not fetch information, and the name of the YAML file for error
    output.

    Returns a tuple(context, resources, uri2resource), where:
      * context is the metric context
      * resources is a dict(key: metric group name, value: list of
        auto-enabled resource objects for the metric group).
      * uri2resource is a dict(key: resource URI, value: auto-enabled resource
        object for the URI).

    Raises: zhmccclient exceptions
    """
    config_mg_dict = config_dict["metric_groups"]
    exported_hmc_metric_groups = []
    exported_res_metric_groups = []
    for metric_group in yaml_metric_groups:
        mg_dict = yaml_metric_groups[metric_group]
        mg_type = mg_dict.get("type", 'hmc')
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
            if mg_type == 'hmc':
                exported_hmc_metric_groups.append(metric_group)
            else:
                assert mg_type == 'resource'  # ensured by enum
                exported_res_metric_groups.append(metric_group)

    client = zhmcclient.Client(session)

    logprint(logging.INFO, PRINT_V,
             "Creating a metrics context on the HMC for HMC metric "
             "groups: {}".format(', '.join(exported_hmc_metric_groups)))
    context = client.metrics_contexts.create(
        {"anticipated-frequency-seconds": 15,
         "metric-groups": exported_hmc_metric_groups})

    resources = {}
    uri2resource = {}
    for metric_group in exported_res_metric_groups:
        logprint(logging.INFO, PRINT_V,
                 "Retrieving resources from the HMC for resource metric "
                 f"group {metric_group}")
        try:
            resource_path = yaml_metric_groups[metric_group]['resource']
        except KeyError:
            new_exc = InvalidMetricDefinitionFile(
                "Missing 'resource' item in resource metric group "
                f"{metric_group} in the metric definition file")
            new_exc.__cause__ = None  # pylint: disable=invalid-name
            raise new_exc
        if resource_path == 'cpc':
            resources[metric_group] = []
            cpcs = client.cpcs.list()
            for cpc in cpcs:
                logprint(logging.INFO, PRINT_V,
                         f"Enabling auto-update for CPC {cpc.name}")
                try:
                    cpc.enable_auto_update()
                except zhmcclient.Error as exc:
                    logprint(logging.ERROR, PRINT_ALWAYS,
                             f"Not providing metric group {metric_group!r} "
                             f"for CPC {cpc.name}, because enabling "
                             "auto-update for it failed with "
                             f"{exc.__class__.__name__}: {exc}")
                    continue  # skip this CPC
                resources[metric_group].append(cpc)
                uri2resource[cpc.uri] = cpc
        elif resource_path == 'cpc.partition':
            resources[metric_group] = []
            cpcs = client.cpcs.list()
            for cpc in cpcs:
                partitions = cpc.partitions.list()
                for partition in partitions:
                    logprint(logging.INFO, PRINT_V,
                             "Enabling auto-update for partition "
                             f"{cpc.name}.{partition.name}")
                    try:
                        partition.enable_auto_update()
                    except zhmcclient.Error as exc:
                        logprint(logging.ERROR, PRINT_ALWAYS,
                                 f"Not providing metric group {metric_group!r} "
                                 f"for partition {cpc.name}.{partition.name}, "
                                 "because enabling auto-update for it failed "
                                 f"with {exc.__class__.__name__}: {exc}")
                        continue  # skip this partition
                    resources[metric_group].append(partition)
                    uri2resource[partition.uri] = partition
        elif resource_path == 'cpc.logical-partition':
            resources[metric_group] = []
            cpcs = client.cpcs.list()
            for cpc in cpcs:
                lpars = cpc.lpars.list()
                for lpar in lpars:
                    logprint(logging.INFO, PRINT_V,
                             "Enabling auto-update for LPAR "
                             f"{cpc.name}.{lpar.name}")
                    try:
                        lpar.enable_auto_update()
                    except zhmcclient.Error as exc:
                        logprint(logging.ERROR, PRINT_ALWAYS,
                                 f"Not providing metric group {metric_group!r} "
                                 f"for LPAR {cpc.name}.{lpar.name}, because "
                                 "enabling auto-update for it failed with "
                                 f"{exc.__class__.__name__}: {exc}")
                        continue  # skip this LPAR
                    resources[metric_group].append(lpar)
                    uri2resource[lpar.uri] = lpar
        elif resource_path == 'console.storagegroup':
            resources[metric_group] = []
            console = client.consoles.console
            storage_groups = console.storage_groups.list()
            for sg in storage_groups:
                logprint(logging.INFO, PRINT_V,
                         f"Enabling auto-update for storage group {sg.name}")
                try:
                    sg.enable_auto_update()
                except zhmcclient.Error as exc:
                    logprint(logging.ERROR, PRINT_ALWAYS,
                             f"Not providing metric group {metric_group!r} for "
                             f"storage group {sg.name}, because enabling "
                             "auto-update for it failed with "
                             f"{exc.__class__.__name__}: {exc}")
                    continue  # skip this storage group
                resources[metric_group].append(sg)
                uri2resource[sg.uri] = sg
        elif resource_path == 'console.storagevolume':
            resources[metric_group] = []
            console = client.consoles.console
            storage_groups = console.storage_groups.list()
            for sg in storage_groups:
                storage_volumes = sg.storage_volumes.list()
                for sv in storage_volumes:
                    logprint(logging.INFO, PRINT_V,
                             "Enabling auto-update for storage volume "
                             f"{sg.name}.{sv.name}")
                    try:
                        sv.enable_auto_update()
                    except zhmcclient.Error as exc:
                        logprint(logging.ERROR, PRINT_ALWAYS,
                                 f"Not providing metric group {metric_group!r} "
                                 f"for storage volume {sg.name}.{sv.name}, "
                                 "because enabling auto-update for it failed "
                                 f"with {exc.__class__.__name__}: {exc}")
                        continue  # skip this storage group
                    resources[metric_group].append(sv)
                    uri2resource[sv.uri] = sv
        else:
            new_exc = InvalidMetricDefinitionFile(
                f"Unknown resource item {resource_path!r} in resource "
                f"metric group {metric_group!r} in the metric definition "
                "file.")
            new_exc.__cause__ = None  # pylint: disable=invalid-name
            raise new_exc

    # Fetch backing adapters of NICs, if needed
    if 'partition-attached-network-interface' in exported_hmc_metric_groups:
        cpcs = client.cpcs.list()
        for cpc in cpcs:
            partitions = cpc.partitions.list()
            for partition in partitions:
                nics = partition.nics.list()
                for nic in nics:

                    logprint(logging.INFO, PRINT_V,
                             "Getting backing adapter port for NIC "
                             f"{cpc.name}.{partition.name}.{nic.name}")
                    adapter_name, port_index = get_backing_adapter_info(nic)

                    # Store the adapter port data as dynamic attributes on the
                    # Nic object in the uri2resource dict.
                    nic.adapter_name = adapter_name
                    nic.port_index = port_index
                    uri2resource[nic.uri] = nic

    return context, resources, uri2resource


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
    Takes the metrics context.
    Returns a zhmcclient.MetricsResponse object.

    Raises: zhmccclient exceptions
    """
    retrieved_metrics = context.get_metrics()
    metrics_object = zhmcclient.MetricsResponse(context, retrieved_metrics)
    return metrics_object


class ResourceCache:
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
            logprint(logging.INFO, PRINT_VV,
                     f"Finding resource for {uri}")
            try:
                _resource = object_value.resource  # Takes time to find on HMC
            except zhmcclient.MetricsResourceNotFound as exc:
                mgd = object_value.metric_group_definition
                logprint(logging.WARNING, PRINT_ALWAYS,
                         f"Did not find resource {uri} specified in metric "
                         f"object value for metric group '{mgd.name}'")
                for mgr in exc.managers:
                    res_class = mgr.class_name
                    logprint(logging.WARNING, PRINT_ALWAYS,
                             f"Details: List of {res_class} resources found:")
                    for res in mgr.list():
                        logprint(logging.WARNING, PRINT_ALWAYS,
                                 f"Details: Resource found: {res.uri} "
                                 f"({res.name})")
                logprint(logging.WARNING, PRINT_ALWAYS,
                         "Details: Current resource cache:")
                for res in self._resources.values():
                    logprint(logging.WARNING, PRINT_ALWAYS,
                             f"Details: Resource cache: {res.uri} ({res.name})")
                raise
            self._resources[uri] = _resource
        return _resource

    def remove(self, uri):
        """
        Remove the resource with a specified URI from the cache, if present.
        If not present, nothing happens.
        """
        try:
            del self._resources[uri]
        except KeyError:
            pass


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


def get_backing_adapter_info(nic):
    """
    Return backing adapter and port of the specified NIC.

    Returns:
      tuple(adapter_name, port_index)
    """

    session = nic.manager.session

    # Handle vswitch-based NIC (OSA, HS)
    try:
        vswitch_uri = nic.get_property('virtual-switch-uri')
    except KeyError:
        pass
    else:
        vswitch_props = session.get(vswitch_uri)
        adapter_uri = vswitch_props['backing-adapter-uri']
        adapter_props = session.get(adapter_uri)
        return adapter_props['name'], vswitch_props['port']

    # Handle adapter-based NIC (RoCE, CNA)
    port_uri = nic.get_property('network-adapter-port-uri')
    port_props = session.get(port_uri)
    adapter_uri = port_props['parent']
    adapter_props = session.get(adapter_uri)
    return adapter_props['name'], port_props['index']


def uri_to_resource(client, uri2resource, uri):
    """
    Look up a zhmcclient resource object from a URI, using the uri2resoure
    dict. If the URI is not in the dict, determine the resource object from
    the URI and add it to the dict. This supports the addition of resources
    after the start of the exporter.

    The following URIs are supported (these are all that are
    currently used by uri2resource and related functions in the
    metric definition file):

      * nic - used in nic metric group (to get back to original NIC object that
        has adapter_name/port as additonal attributes)
      * storage groups - used in partition metric group
      * cpc - used in storage-group and storage-volume metric groups
    """

    try:
        resource = uri2resource[uri]
    except KeyError:
        # The uri2resource dict was created at startup time of the
        # exporter and was filled with all resources (of types the exporter
        # supports) that existed at that time. The KeyError means that
        # a new resource came into existence since then.

        m = re.match(r'(/api/partitions/[a-f0-9\-]+)/nics/[a-f0-9\-]+$', uri)
        if m is not None:
            # Resource URI is for a NIC
            partition_uri = m.group(1)
            partition_props = client.session.get(partition_uri)
            cpc_uri = partition_props['parent']
            cpc = client.cpcs.resource_object(cpc_uri)
            partition = cpc.partitions.resource_object(partition_uri)
            nic = partition.nics.resource_object(uri)
            logprint(logging.INFO, PRINT_V,
                     f"Adding NIC {cpc.name}.{partition.name}.{nic.name} "
                     "after exporter start for fast lookup")
            uri2resource[uri] = nic
            return nic

        m = re.match(r'(/api/storage-groups/[a-f0-9\-]+)$', uri)
        if m is not None:
            # Resource URI is for a storage group
            console = client.consoles.console
            stogrp = console.storage_groups.resource_object(uri)
            # Get the CPC via 'uri2resource()' because that avoids the
            # "Get CPC Properties" operation that is performed when getting it
            # via the 'cpc' property on the storage group object.
            cpc_uri = stogrp.get_property('cpc-uri')
            cpc = uri_to_resource(client, uri2resource, cpc_uri)
            logprint(logging.INFO, PRINT_V,
                     f"Adding storage group {cpc.name}.{stogrp.name} "
                     "after exporter start for fast lookup")
            uri2resource[uri] = stogrp
            return stogrp

        m = re.match(r'(/api/cpcs/[a-f0-9\-]+)$', uri)
        if m is not None:
            # Resource URI is for a CPC
            cpc = client.cpcs.resource_object(uri)
            logprint(logging.INFO, PRINT_V,
                     f"Adding CPC {cpc.name} after exporter start for "
                     "fast lookup")
            uri2resource[uri] = cpc
            return cpc

        raise OtherError(
            f"Resource type for URI {uri} is not supported for dynamic "
            "addition of resources after start of exporter")

    return resource


def expand_group_label_value(
        env, label_name, group_name, item_value, client, resource_obj,
        uri2resource, metric_values=None):
    """
    Expand a Jinja2 expression on a label value, for a metric group label.
    """

    def uri2resource_func(uri):
        return uri_to_resource(client, uri2resource, uri)

    def uris2resources_func(uris):
        return [uri_to_resource(client, uri2resource, uri) for uri in uris]

    def adapter_name_func(nic):
        # Get the original Nic object that has the dynamic attributes with the
        # adapter info
        nic_org = uri_to_resource(client, uri2resource, nic.uri)
        return nic_org.adapter_name

    def adapter_port_func(nic):
        # Get the original Nic object that has the dynamic attributes with the
        # adapter info
        nic_org = uri_to_resource(client, uri2resource, nic.uri)
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
        env, label_name, metric_exporter_name, item_value, client,
        resource_obj, uri2resource, metric_values=None):
    """
    Expand a Jinja2 expression on a label value, for a metric label.
    """

    def uri2resource_func(uri):
        return uri_to_resource(client, uri2resource, uri)

    def uris2resources_func(uris):
        return [uri_to_resource(client, uri2resource, uri) for uri in uris]

    def adapter_name_func(nic):
        # Get the original Nic object that has the dynamic attributes with the
        # adapter info
        nic_org = uri_to_resource(client, uri2resource, nic.uri)
        return nic_org.adapter_name

    def adapter_port_func(nic):
        # Get the original Nic object that has the dynamic attributes with the
        # adapter info
        nic_org = uri_to_resource(client, uri2resource, nic.uri)
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


def cpc_from_resource(resource):
    """
    From a given zhmcclient resource object, try to navigate to its CPC
    and return the zhmcclient.Cpc object.
    If the resource is not a CPC or part of a CPC, return None.
    """
    cpc = resource
    while True:
        if cpc is None or cpc.manager.class_name == 'cpc':
            break
        cpc = cpc.manager.parent
    return cpc


def build_family_objects(
        metrics_object, yaml_metric_groups, yaml_metrics,
        extra_labels, hmc_version, hmc_api_version, hmc_features,
        se_versions_by_cpc, se_features_by_cpc, session, resource_cache=None,
        uri2resource=None):
    """
    Go through all retrieved metrics and build the Prometheus Family objects.

    Note: resource_cache and uri2resource will be omitted in tests, and is
    therefore optional.

    Returns a dictionary of Prometheus Family objects with the following
    structure:

      family_name:
        GaugeMetricFamily object
    """
    env = jinja2.Environment(autoescape=True)
    client = zhmcclient.Client(session)

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
            if resource_cache:
                try:
                    resource = resource_cache.resource(
                        object_value.resource_uri, object_value)
                except zhmcclient.MetricsResourceNotFound:
                    # Some details have already been logged & printed
                    warnings.warn(
                        f"The HMC metric group {metric_group!r} contains a "
                        f"resource with URI '{object_value.resource_uri}' "
                        "that is not found on the HMC. Please open an exporter "
                        "issue for that.")
                    continue  # Skip this metric
            else:
                resource = object_value.resource
            metric_values = object_value.metrics

            cpc = cpc_from_resource(resource)
            if cpc:
                # This resource is a CPC or part of a CPC
                se_version = se_versions_by_cpc[cpc.name]
                se_features = se_features_by_cpc[cpc.name]
            else:
                # This resource is an HMC or part of an HMC
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
                    env, label_name, metric_group, item_value, client,
                    resource, uri2resource, metric_values)
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
                        item_value, client, resource, uri2resource,
                        metric_values)
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
        resources, yaml_metric_groups, yaml_metrics,
        extra_labels, hmc_version, hmc_api_version, hmc_features,
        se_versions_by_cpc, se_features_by_cpc, session, resource_cache=None,
        uri2resource=None):
    """
    Go through all auto-updated resources and build the Prometheus Family
    objects for them.

    Note: resource_cache and uri2resource will be omitted in tests, and is
    therefore optional.

    Returns a dictionary of Prometheus Family objects with the following
    structure:

      family_name:
        GaugeMetricFamily object
    """
    env = jinja2.Environment(autoescape=True)
    client = zhmcclient.Client(session)

    family_objects = {}
    for metric_group, res_list in resources.items():

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

            cpc = cpc_from_resource(resource)
            if cpc:
                # This resource is a CPC or part of a CPC
                se_version = se_versions_by_cpc[cpc.name]
                se_features = se_features_by_cpc[cpc.name]
            else:
                # This resource is an HMC or part of an HMC
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
                    env, label_name, metric_group, item_value, client,
                    resource, uri2resource)
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
                        env, label_name, exporter_name, item_value, client,
                        resource, uri2resource)
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

    def __init__(self, config_dict, session, context, resources,
                 yaml_metric_groups, yaml_metrics, yaml_fetch_properties,
                 extra_labels, metrics_filename, config_filename,
                 resource_cache, uri2resource, hmc_version, hmc_api_version,
                 hmc_features, se_versions_by_cpc, se_features_by_cpc):
        self.config_dict = config_dict
        self.session = session
        self.context = context
        self.resources = resources
        self.yaml_metric_groups = yaml_metric_groups
        self.yaml_metrics = yaml_metrics
        self.yaml_fetch_properties = yaml_fetch_properties
        self.extra_labels = extra_labels
        self.metrics_filename = metrics_filename
        self.config_filename = config_filename
        self.resource_cache = resource_cache
        self.uri2resource = uri2resource
        self.hmc_version = hmc_version
        self.hmc_api_version = hmc_api_version
        self.hmc_features = hmc_features
        self.se_versions_by_cpc = se_versions_by_cpc
        self.se_features_by_cpc = se_features_by_cpc
        self.fetch_thread = None
        self.fetch_event = None
        self.last_export_dt = None
        self.export_interval = None

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

        with zhmc_exceptions(self.session, self.config_filename):

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
                                 "Recreating the metrics context after HTTP "
                                 f"status {exc.http_status}.{exc.reason}")
                        self.context, _, _ = create_metrics_context(
                            self.session, self.config_dict,
                            self.yaml_metric_groups,
                            self.hmc_version, self.hmc_api_version,
                            self.hmc_features)
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
                             "Abandoning after server authentication error: "
                             f"{exc}")
                    raise
                except zhmcclient.ClientAuthError as exc:
                    logprint(logging.ERROR, PRINT_ALWAYS,
                             "Abandoning after client authentication error: "
                             f"{exc}")
                    raise
                # pylint: disable=broad-exception-caught,broad-except
                except Exception as exc:
                    tb_str = traceback.format_tb(exc.__traceback__, limit=-1)[0]
                    logprint(logging.ERROR, PRINT_ALWAYS,
                             "Abandoning after exception "
                             f"{exc.__class__.__name__}: {exc}\n{tb_str}")
                    raise
                break

        logprint(logging.DEBUG, None,
                 "Building family objects for HMC metrics")
        family_objects = build_family_objects(
            metrics_object, self.yaml_metric_groups, self.yaml_metrics,
            self.extra_labels, self.hmc_version, self.hmc_api_version,
            self.hmc_features, self.se_versions_by_cpc, self.se_features_by_cpc,
            self.session, self.resource_cache, self.uri2resource)

        logprint(logging.DEBUG, None,
                 "Building family objects for resource metrics")
        family_objects.update(build_family_objects_res(
            self.resources, self.yaml_metric_groups, self.yaml_metrics,
            self.extra_labels, self.hmc_version, self.hmc_api_version,
            self.hmc_features, self.se_versions_by_cpc, self.se_features_by_cpc,
            self.session, self.resource_cache, self.uri2resource))

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
            for lpar in console.list_permitted_lpars(
                    additional_properties=lpar_props):
                updated_resources[lpar.uri] = lpar
            for cpc in client.cpcs.list():
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
                try:
                    res = self.uri2resource[uri]
                except KeyError:
                    continue
                res.update_properties_local(updated_res.properties)
            for fetch_item in self.yaml_fetch_properties.values():
                for metric_group in fetch_item["metric-groups"]:
                    try:
                        resources = self.resources[metric_group]
                    except KeyError:
                        continue
                    for res in resources:
                        try:
                            updated_res = updated_resources[res.uri]
                        except KeyError:
                            continue
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


# Global variable with the verbosity level from the command line
VERBOSE_LEVEL = 0

# Global variable indicating that logging is enabled
LOGGING_ENABLED = False


def logprint(log_level, print_level, message):
    """
    Log a message at the specified log level, and print the message at
    the specified verbosity level

    Parameters:
        log_level (int): Python logging level at which the message should be
          logged (logging.DEBUG, etc.), or None for no logging.
        print_level (int): Verbosity level at which the message should be
          printed (1, 2), or None for no printing.
        message (string): The message.
    """
    if print_level is not None and VERBOSE_LEVEL >= print_level:
        print(message)
    if log_level is not None and LOGGING_ENABLED:
        logger = logging.getLogger(EXPORTER_LOGGER_NAME)
        # Note: This method never raises an exception. Errors during logging
        # are handled by calling handler.handleError().
        logger.log(log_level, message)


def setup_logging(log_dest, log_complevels, syslog_facility):
    """
    Set up Python logging as specified in the command line.

    Raises:
        EarlyExit
    """
    global LOGGING_ENABLED  # pylint: disable=global-statement

    if log_dest is None:
        logprint(None, PRINT_V, "Logging is disabled")
        handler = None
        dest_str = None
    elif log_dest == 'stderr':
        dest_str = "the Standard Error stream"
        logprint(None, PRINT_V, f"Logging to {dest_str}")
        handler = logging.StreamHandler(stream=sys.stderr)
    elif log_dest == 'syslog':
        system = platform.system()
        if system.startswith('CYGWIN_NT'):
            # Value is 'CYGWIN_NT-6.1'; strip off trailing version:
            system = 'CYGWIN_NT'
        try:
            address = SYSLOG_ADDRESS[system]
        except KeyError:
            address = SYSLOG_ADDRESS['other']
        dest_str = (
            f"the System Log at address {address!r} with syslog facility "
            f"{syslog_facility!r}")
        logprint(None, PRINT_V, f"Logging to {dest_str}")
        try:
            facility = logging.handlers.SysLogHandler.facility_names[
                syslog_facility]
        except KeyError:
            valid_slfs = ', '.join(
                logging.handlers.SysLogHandler.facility_names.keys())
            raise EarlyExit(
                f"This system ({system}) does not support syslog facility "
                f"{syslog_facility}. Supported are: {valid_slfs}.")
        # The following does not raise any exception if the syslog address
        # cannot be opened. In that case, the first attempt to log something
        # will fail.
        handler = logging.handlers.SysLogHandler(
            address=address, facility=facility)
    else:
        dest_str = f"file {log_dest}"
        logprint(None, PRINT_V, f"Logging to {dest_str}")
        try:
            handler = logging.FileHandler(log_dest)
        except OSError as exc:
            raise EarlyExit(
                f"Cannot log to file {log_dest}: {exc.__class__.__name__}: "
                f"{exc}")

    if not handler and log_complevels:
        raise EarlyExit(
            "--log-comp option cannot be used when logging is disabled; "
            "use --log option to enable logging.")

    if handler:

        def handleError(self, record):
            """
            Replacement for built-in method on logging.Handler class.

            This is needed because the SysLogHandler class does not raise
            an exception when creating the handler object, but only when
            logging something to it.
            """
            _, exc, _ = sys.exc_info()
            f_record = self.format(record)
            print(f"Error: Logging to {dest_str} failed with: "
                  f"{exc.__class__.__name__}: {exc}. Formatted log record: "
                  f"{f_record!r}",
                  file=sys.stderr)
            sys.exit(1)

        handler.handleError = types.MethodType(handleError, handler)

        logger_level_dict = {}  # key: logger_name, value: level
        if not log_complevels:
            log_complevels = [DEFAULT_LOG_COMP]
        for complevel in log_complevels:
            if '=' in complevel:
                comp, level = complevel.split('=', 2)
            else:
                comp = complevel
                level = DEFAULT_LOG_LEVEL
            if level not in LOG_LEVELS:
                allowed = ', '.join(VALID_LOG_LEVELS)
                raise EarlyExit(
                    f"Invalid log level {level!r} in --log-comp option. "
                    f"Allowed are: {allowed}")
            if comp == 'all':
                for logger_name in LOGGER_NAMES.values():
                    logger_level_dict[logger_name] = level
            else:
                try:
                    logger_name = LOGGER_NAMES[comp]
                except KeyError:
                    allowed = ', '.join(VALID_LOG_COMPONENTS)
                    raise EarlyExit(
                        f"Invalid component {comp!r} in --log-comp option. "
                        f"Allowed are: {allowed}")
                logger_level_dict[logger_name] = level

        complevels = ', '.join(
            [f"{name}={level}"
             for name, level in logger_level_dict.items()])
        logprint(None, PRINT_V,
                 f"Logging components: {complevels}")

        if isinstance(handler, logging.handlers.SysLogHandler):
            # Most syslog implementations fail when the message is longer
            # than a limit. We use a hard coded limit for now:
            # * 2048 is the typical maximum length of a syslog message,
            #   including its headers
            # * 41 is the max length of the syslog message parts before MESSAGE
            # * 47 is the max length of the Python format string before message
            # Example syslog message:
            #   <34>1 2003-10-11T22:14:15.003Z localhost MESSAGE
            # where MESSAGE is the formatted Python log message.
            max_msg = f'.{2048 - 41 - 47}'
        else:
            max_msg = ''
        fs = ('%(asctime)s %(threadName)s %(levelname)s %(name)s: '
              '%(message){m}s'.format(m=max_msg))

        # Set the formatter to always log times in UTC. Since the %z
        # formatting string does not get adjusted for that, set the timezone
        # offset always to '+0000'.
        dfs = '%Y-%m-%d %H:%M:%S+0000'
        logging.Formatter.converter = time.gmtime  # log times in UTC

        handler.setFormatter(logging.Formatter(fmt=fs, datefmt=dfs))
        for logger_name in LOGGER_NAMES.values():
            logger = logging.getLogger(logger_name)
            if logger_name in logger_level_dict:
                level = logger_level_dict[logger_name]
                level_int = LOG_LEVELS[level]
                if level_int != logging.NOTSET:
                    logger.addHandler(handler)
                logger.setLevel(level_int)
            else:
                logger.setLevel(logging.NOTSET)

        LOGGING_ENABLED = True


def main():
    """Puts the exporter together."""
    # If the session and context keys are not created, their destruction
    # should not be attempted.

    global VERBOSE_LEVEL  # pylint: disable=global-statement

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

        VERBOSE_LEVEL = args.verbose

        setup_logging(args.log_dest, args.log_complevels, args.syslog_facility)

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
                 f"Verbosity level: {VERBOSE_LEVEL}")

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

        logprint(logging.INFO, PRINT_V,
                 "Timeout/retry configuration: "
                 f"connect: {RETRY_TIMEOUT_CONFIG.connect_timeout} sec / "
                 f"{RETRY_TIMEOUT_CONFIG.connect_retries} retries, "
                 f"read: {RETRY_TIMEOUT_CONFIG.read_timeout} sec / "
                 f"{RETRY_TIMEOUT_CONFIG.read_retries} retries.")

        env = jinja2.Environment(autoescape=True)

        session = create_session(config_dict, config_filename)

        try:
            with zhmc_exceptions(session, config_filename):
                hmc_info = get_hmc_info(session)
                hmc_version = split_version(hmc_info['hmc-version'], 3)
                hmc_api_version = (hmc_info['api-major-version'],
                                   hmc_info['api-minor-version'])
                client = zhmcclient.Client(session)
                hmc_features = client.consoles.console.list_api_features()
                cpc_list = client.cpcs.list()

                se_versions_by_cpc = {}
                se_features_by_cpc = {}
                for cpc in cpc_list:
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
                for cpc in cpc_list:
                    cpc_name = cpc.name
                    se_version_str = version_str(se_versions_by_cpc[cpc_name])
                    logprint(logging.INFO, PRINT_V,
                             f"SE version of CPC {cpc_name}: {se_version_str}")
                for cpc in cpc_list:
                    cpc_name = cpc.name
                    se_features_str = ', '.join(se_features_by_cpc[cpc_name]) \
                        or 'None'
                    logprint(logging.INFO, PRINT_V,
                             f"SE features of CPC {cpc_name}: "
                             f"{se_features_str}")

                context, resources, uri2resource = create_metrics_context(
                    session, config_dict, yaml_metric_groups,
                    hmc_version, hmc_api_version, hmc_features)

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

        resource_cache = ResourceCache()
        coll = ZHMCUsageCollector(
            config_dict, session, context, resources, yaml_metric_groups,
            yaml_metrics, yaml_fetch_properties, extra_labels, metrics_filename,
            config_filename, resource_cache, uri2resource, hmc_version,
            hmc_api_version, hmc_features, se_versions_by_cpc,
            se_features_by_cpc)

        logprint(logging.INFO, PRINT_V,
                 "Registering the collector and performing first collection")
        REGISTRY.register(coll)  # Performs a first collection

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

        logprint(logging.INFO, PRINT_V,
                 "Starting thread for fetching properties in background "
                 "for which change notification is not supported")
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
