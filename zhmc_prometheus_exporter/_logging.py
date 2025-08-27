# Copyright 2018,2025 IBM Corp. All Rights Reserved.
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
Logging support for the exporter.
"""

import sys
import platform
import types
import time
import logging

import zhmcclient

from ._exceptions import EarlyExit

# Logger name for the exporter
EXPORTER_LOGGER_NAME = 'zhmcexporter'

# Values for printing messages dependent on verbosity level in command line
PRINT_ALWAYS = 0
PRINT_V = 1
PRINT_VV = 2

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


def setup_logging(log_dest, log_complevels, syslog_facility, verbose_level):
    """
    Set up Python logging as specified in the command line.

    Raises:
        EarlyExit
    """
    global LOGGING_ENABLED  # pylint: disable=global-statement
    global VERBOSE_LEVEL  # pylint: disable=global-statement

    VERBOSE_LEVEL = verbose_level

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
