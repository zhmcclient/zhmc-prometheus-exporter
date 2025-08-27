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
A resource cache for resources needed for metric-based metric groups.
"""

import logging
import zhmcclient
from ._logging import PRINT_ALWAYS, PRINT_VV, logprint


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
                DISPLAY_CACHE = False
                if DISPLAY_CACHE:
                    for mgr in exc.managers:
                        res_class = mgr.class_name
                        logprint(logging.WARNING, PRINT_ALWAYS,
                                 f"Details: List of {res_class} resources "
                                 "found:")
                        for res in mgr.list():
                            logprint(logging.WARNING, PRINT_ALWAYS,
                                     f"Details: Resource found: {res.uri} "
                                     f"({res.name})")
                    logprint(logging.WARNING, PRINT_ALWAYS,
                             "Details: Current resource cache:")
                    for res in self._resources.values():
                        logprint(logging.WARNING, PRINT_ALWAYS,
                                 f"Details: Resource cache: {res.uri} "
                                 f"({res.name})")
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
