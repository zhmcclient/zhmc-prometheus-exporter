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


"""
Unit test module for the _resource_cache.py module.
"""

import pytest
from zhmc_prometheus_exporter._resource_cache import ResourceClassNotSupported


@pytest.mark.parametrize(
    "uri", [
        '/api/cpc/oid1',
        None,
    ]
)
def test_rcns_all(uri):
    """
    Test the ResourceClassNotSupported exception class.
    """
    exp_msg = ("The resource cache does not support the resource "
               f"class in URI {uri!r}")
    exp_repr = f"ResourceClassNotSupported({exp_msg!r}, uri={uri!r})"

    exc = ResourceClassNotSupported(uri)

    act_uri = exc.uri
    assert act_uri == uri

    act_str = str(exc)
    assert act_str == exp_msg

    assert len(exc.args) == 1

    act_args0 = exc.args[0]
    assert act_args0 == exp_msg

    act_repr = repr(exc)
    assert act_repr == exp_repr
