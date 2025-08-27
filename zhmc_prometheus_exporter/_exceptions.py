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
Exceptions used by the exporter.
"""

from contextlib import contextmanager
import zhmcclient


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
