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

"""Unit tests for the zhmc_prometheus_exporter"""

import re
import time
import datetime
import hashlib
import os
import sys
import unittest
import stat  # pylint: disable=wrong-import-order  # reported on Windows

import pytest
import zhmcclient
import zhmcclient_mock

from zhmc_prometheus_exporter.vendor import prometheus_client
from zhmc_prometheus_exporter import zhmc_prometheus_exporter


class TestParseArgs(unittest.TestCase):
    """Tests parse_args."""

    def test_args_store(self):
        """Tests generic input."""
        args = (zhmc_prometheus_exporter.
                parse_args(["-p", "1", "-c", "2"]))
        self.assertEqual(args.p, "1")
        self.assertEqual(args.c, "2")

    def test_default_args(self):
        """Tests for all defaults."""
        args = zhmc_prometheus_exporter.parse_args([])
        self.assertEqual(args.p, None)
        self.assertEqual(args.c, "/etc/zhmc-prometheus-exporter/config.yaml")


class TestParseYaml(unittest.TestCase):
    """Tests parse_yaml_file."""

    def test_normal_input(self):
        """Tests if some generic file is correctly parsed."""
        # Get a SHA256 of Unixtime to create a filename that does not exist
        filename = str(hashlib.sha256(str(time.time()).encode("utf-8")).
                       hexdigest())
        with open(filename, "w+", encoding='utf-8') as testfile:
            testfile.write("""metrics:
  hmc: 127.0.0.1
  userid: user
  password: pwd
""")
        expected_dict = {"metrics": {"hmc": "127.0.0.1",
                                     "userid": "user",
                                     "password": "pwd"}}
        self.assertEqual(
            zhmc_prometheus_exporter.parse_yaml_file(filename, 'test file'),
            expected_dict)
        os.remove(filename)

    def test_permission_error(self):
        """Tests if permission denied is correctly handled."""

        if sys.platform == 'win32':
            pytest.skip("Test not supported on Windows")

        filename = str(hashlib.sha256(str(time.time()).encode("utf-8")).
                       hexdigest())
        with open(filename, "w+", encoding='utf-8'):
            pass
        # Make it unreadable (mode 000)
        os.chmod(filename, not stat.S_IRWXU)
        with self.assertRaises(zhmc_prometheus_exporter.ImproperExit):
            zhmc_prometheus_exporter.parse_yaml_file(
                filename, 'test file')
        os.remove(filename)

    def test_not_found_error(self):
        """Tests if file not found is correctly handled."""
        filename = str(hashlib.sha256(str(time.time()).encode("utf-8")).
                       hexdigest())
        with self.assertRaises(zhmc_prometheus_exporter.ImproperExit):
            zhmc_prometheus_exporter.parse_yaml_file(filename, 'test file')


TESTCASES_SPLIT_VERSION = [
    # (version_str, pad_to, exp_result)
    ('', 0, (0,)),
    ('', 1, (0,)),
    ('', 2, (0, 0)),
    ('.', 0, (0, 0)),
    ('.', 2, (0, 0)),
    ('.', 3, (0, 0, 0)),
    ('1', 0, (1,)),
    ('1', 1, (1,)),
    ('1', 2, (1, 0)),
    ('1.', 0, (1, 0)),
    ('1.', 2, (1, 0)),
    ('1.', 3, (1, 0, 0)),
    ('1.2', 0, (1, 2)),
    ('1.2', 2, (1, 2)),
    ('1.2', 3, (1, 2, 0)),
    ('13.23.42', 0, (13, 23, 42)),
    ('1.002', 0, (1, 2)),
]


@pytest.mark.parametrize(
    "version_str, pad_to, exp_result", TESTCASES_SPLIT_VERSION
)
def test_split_version(version_str, pad_to, exp_result):
    """
    Tests split_version().
    """

    # The code to be tested
    result = zhmc_prometheus_exporter.split_version(version_str, pad_to)

    assert result == exp_result


TESTCASES_EVAL_CONDITION = [
    # (condition, hmc_version_str, se_version_str, exp_result)
    ('True', '', '', True),
    ('False', '', '', False),
    ('"a" == "a"', '', '', True),
    ('1 == 1', '', '', True),
    ('1 >= 1', '', '', True),
    ('1 > 1', '', '', False),
    ('hmc_version == "2.14"', '2.14', '2.13', True),
    ("hmc_version == '2.14'", '2.14', '2.13', True),
    ("hmc_version >= '2.14'", '2.4', '2.13', False),
    ("hmc_version >= '2.14'", '2.14.0', '2.13', True),
    ("hmc_version >= '2.14'", '2.14.1', '2.13', True),
    ("hmc_version <= '2.14'", '2.14.0', '2.13', True),
    ("hmc_version <= '2.14'", '2.14.1', '2.13', False),
    ("hmc_version >= '2.14.0'", '2.14', '2.13', True),
    ("hmc_version >= '2.14.1'", '2.14', '2.13', False),
    ("hmc_version <= '2.14.0'", '2.14', '2.13', True),
    ("hmc_version <= '2.14.1'", '2.14', '2.13', True),
    ("hmc_version >= '2.14' and hmc_version <= '2.15'", '2.14', '2.13', True),
    ("hmc_version >= '2.14' and hmc_version <= '2.15'", '2.16', '2.13', False),
    ('se_version == "2.13"', '2.14', '2.13', True),
    ("se_version == '2.13'", '2.14', '2.13', True),
    ("se_version >= '2.13'", '2.14', '2.3', False),
    ("se_version >= '2.13'", '2.14', '2.13.0', True),
    ("se_version >= '2.13'", '2.14', '2.13.1', True),
    ("se_version <= '2.13'", '2.14', '2.13.0', True),
    ("se_version <= '2.13'", '2.14', '2.13.1', False),
    ("se_version >= '2.13.0'", '2.14', '2.13', True),
    ("se_version >= '2.13.1'", '2.14', '2.13', False),
    ("se_version <= '2.13.0'", '2.14', '2.13', True),
    ("se_version <= '2.13.1'", '2.14', '2.13', True),
    ("se_version >= '2.13' and se_version <= '2.14'", '2.14', '2.13', True),
    ("se_version >= '2.13' and se_version <= '2.14'", '2.14', '2.15', False),
]


@pytest.mark.parametrize(
    "condition, hmc_version_str, se_version_str, exp_result",
    TESTCASES_EVAL_CONDITION
)
def test_eval_condition_versions(
        condition, hmc_version_str, se_version_str, exp_result):
    """
    Tests eval_condition() with hmc_version and se_version variables.
    """

    session = setup_faked_session()
    client = zhmcclient.Client(session)
    cpc = client.cpcs.find(name='cpc_1')

    # Arbitrary values for these variables, since we are not testing that here:
    hmc_api_version = (4, 10)
    hmc_version = zhmc_prometheus_exporter.split_version(hmc_version_str, 3)
    se_version = zhmc_prometheus_exporter.split_version(se_version_str, 3)
    hmc_features = []
    se_features = []
    resource_obj = cpc  # to indicate it is a export-condition

    # The code to be tested
    result = zhmc_prometheus_exporter.eval_condition(
        "", condition, hmc_version, hmc_api_version, hmc_features, se_version,
        se_features, resource_obj)

    assert result == exp_result


def test_eval_condition_resource():
    """
    Tests eval_condition() with resource_obj variable.
    """
    session = setup_faked_session()
    client = zhmcclient.Client(session)
    cpc = client.cpcs.find(name='cpc_1')

    # Arbitrary values for these variables, since we are not testing that here:
    hmc_version = (2, 16, 0)
    hmc_api_version = (4, 10)
    hmc_features = []
    se_version = (2, 15, 0)
    se_features = []

    resource_obj = cpc
    condition = 'resource_obj.name'

    # The code to be tested
    result = zhmc_prometheus_exporter.eval_condition(
        "", condition, hmc_version, hmc_api_version, hmc_features, se_version,
        se_features, resource_obj)

    assert result == 'cpc_1'


TESTCASES_EVAL_CONDITION_ERROR = [
    # (condition, warn_msg_pattern)
    ('dir()', "NameError: name 'dir' is not defined"),
    ('builtins.dir()', "NameError: name 'builtins' is not defined"),
    ('__builtins__["dir"]', "KeyError: 'dir'"),
]


@pytest.mark.parametrize(
    "condition, warn_msg_pattern",
    TESTCASES_EVAL_CONDITION_ERROR
)
def test_eval_condition_error(condition, warn_msg_pattern):
    """
    Tests eval_condition() with evaluation errors.
    """
    session = setup_faked_session()
    client = zhmcclient.Client(session)
    cpc = client.cpcs.find(name='cpc_1')

    # Arbitrary values for these variables, since we are not testing that here:
    hmc_version = (2, 16, 0)
    hmc_api_version = (4, 10)
    hmc_features = []
    se_version = (2, 15, 0)
    se_features = []
    resource_obj = cpc

    with pytest.warns(UserWarning) as warn_records:

        # The code to be tested
        zhmc_prometheus_exporter.eval_condition(
            "", condition, hmc_version, hmc_api_version, hmc_features,
            se_version, se_features, resource_obj)

    # Evaluation errors surface as one UserWarning
    assert len(warn_records) == 1
    warn_record = warn_records[0]
    assert re.search(warn_msg_pattern, str(warn_record.message))


# Fake HMC derived from
# github.com/zhmcclient/python-zhmcclient/zhmcclient_mock/_hmc.py
class TestCreateContext(unittest.TestCase):
    """Tests create_metrics_context with a fake HMC."""

    def test_normal_input(self):
        """Tests normal input with a generic metric group."""

        hmc_version = '2.13.1'
        hmc_api_version_str = '1.8'
        hmc_api_version = (1, 8)
        hmc_features = []

        session = zhmcclient_mock.FakedSession(
            "fake-host", "fake-hmc", hmc_version, hmc_api_version_str)
        config_dict = {
            "metric_groups": {
                "dpm-system-usage-overview": {"export": True},
            }
        }
        yaml_metric_groups = {
            "dpm-system-usage-overview": {"prefix": "pre"},
        }
        context, _, _ = zhmc_prometheus_exporter.create_metrics_context(
            session, config_dict, yaml_metric_groups, hmc_version,
            hmc_api_version, hmc_features)
        # pylint: disable=protected-access
        self.assertEqual(type(context), zhmcclient._metrics.MetricsContext)
        context.delete()
        session.logoff()

    def test_timeout(self):
        """Tests a timeout with an IP where no HMC is sitting."""

        hmc_version = '2.14.1'
        hmc_api_version = (2, 37)
        hmc_features = []
        config_dict = {
            "hmcs": [
                {"host": "192.168.0.0", "userid": "user", "password": "pwd"}
            ],
        }
        session = zhmc_prometheus_exporter.create_session(
            config_dict, "filename")
        config_dict = {
            "hmcs": [
                {"host": "192.168.0.0", "userid": "user", "password": "pwd"}
            ],
            "metric_groups": {}
        }
        yaml_metric_groups = {}
        with self.assertRaises(zhmcclient.ConnectionError):
            zhmc_prometheus_exporter.create_metrics_context(
                session, config_dict, yaml_metric_groups, hmc_version,
                hmc_api_version, hmc_features)


class TestCleanup(unittest.TestCase):
    """Tests cleanup."""

    def test_clecnup(self):
        # pylint: disable=no-self-use
        """Tests normal input, just needs to know no errors happen."""
        session = zhmcclient_mock.FakedSession("fake-host", "fake-hmc",
                                               "2.13.1", "1.8")
        client = zhmcclient.Client(session)
        context = client.metrics_contexts.create(
            {"anticipated-frequency-seconds": 15,
             "metric-groups": ["dpm-system-usage-overview"]})
        zhmc_prometheus_exporter.cleanup(session, context, None, None)


def setup_faked_session():
    """Create a faked session."""

    session = zhmcclient_mock.FakedSession("fake-host", "fake-hmc",
                                           "2.13.1", "1.8")
    session.hmc.add_resources({
        "cpcs": [{
            "properties": {
                "name": "cpc_1",
                "object-id": "cpc_1",
                "object-uri": "/api/cpcs/cpc_1",
            }
        }]
    })
    session.hmc.add_metric_values(
        zhmcclient_mock.FakedMetricObjectValues(
            group_name="dpm-system-usage-overview",
            resource_uri="/api/cpcs/cpc_1",
            timestamp=datetime.datetime.now(),
            values=[
                ("processor-usage", 1),
                ("network-usage", 2),
                ("storage-usage", 3),
                ("accelerator-usage", 4),
                ("crypto-usage", 5),
                ("power-consumption-watts", 100),
                ("temperature-celsius", 10),
                ("cp-shared-processor-usage", 1),
                ("cp-dedicated-processor-usage", 2),
                ("ifl-shared-processor-usage", 3),
                ("ifl-dedicated-processor-usage", 4),
            ]))
    return session


def setup_metrics_context():
    """
    Create a faked session and return a faked metrics context and resources.
    """

    session = setup_faked_session()
    client = zhmcclient.Client(session)
    context = client.metrics_contexts.create(
        {"anticipated-frequency-seconds": 15,
         "metric-groups": ["dpm-system-usage-overview"]})
    resources = {}
    resources["cpc-resource"] = [client.cpcs.find(name='cpc_1')]
    return session, context, resources


def teardown_metrics_context(context):
    """Delete a faked metrics context."""
    context.delete()


class TestMetrics(unittest.TestCase):
    """Tests metrics."""

    def test_retrieve_metrics(self):
        # pylint: disable=no-self-use
        """Tests retrieve_metrics()"""

        _, context, _ = setup_metrics_context()

        metrics_object = zhmc_prometheus_exporter.retrieve_metrics(context)

        assert isinstance(metrics_object, zhmcclient.MetricsResponse)
        assert len(metrics_object.metric_group_values) == 1
        mgv = metrics_object.metric_group_values[0]
        assert mgv.name == 'dpm-system-usage-overview'
        assert len(mgv.object_values) == 1
        ov = mgv.object_values[0]
        assert ov.resource.name == 'cpc_1'
        assert ov.metrics == {
            'processor-usage': 1,
            'network-usage': 2,
            'storage-usage': 3,
            'accelerator-usage': 4,
            'crypto-usage': 5,
            'power-consumption-watts': 100,
            'temperature-celsius': 10,
            'cp-shared-processor-usage': 1,
            'cp-dedicated-processor-usage': 2,
            'ifl-shared-processor-usage': 3,
            'ifl-dedicated-processor-usage': 4,
        }

        teardown_metrics_context(context)

    def test_build_family_objects(self):
        """Tests build_family_objects() and build_family_objects_res()"""

        yaml_metric_groups = {
            "dpm-system-usage-overview": {
                "prefix": "pre",
            },
            "cpc-resource": {
                "type": "resource",
                "resource": "cpc",
                "prefix": "foo",
            }
        }
        yaml_metrics = {
            "dpm-system-usage-overview": {
                "processor-usage": {
                    "percent": True,
                    "exporter_name": "processor_usage",
                    "exporter_desc": "processor_usage description",
                }
            },
            "cpc-resource": {
                "name": {
                    "percent": False,
                    "exporter_name": "name",
                    "exporter_desc": "CPC name",
                }
            }
        }
        extra_labels = {"label1": "value1"}
        hmc_version = '2.15.0'
        hmc_api_version = (3, 13)
        hmc_features = []
        se_versions_by_cpc = {'cpc_1': '2.15.0'}
        se_features_by_cpc = {'cpc_1': []}

        session, context, resources = setup_metrics_context()
        metrics_object = zhmc_prometheus_exporter.retrieve_metrics(context)

        families = zhmc_prometheus_exporter.build_family_objects(
            metrics_object, yaml_metric_groups, yaml_metrics,
            extra_labels, hmc_version, hmc_api_version, hmc_features,
            se_versions_by_cpc, se_features_by_cpc, session)

        assert len(families) == 1
        assert "zhmc_pre_processor_usage" in families
        family = families["zhmc_pre_processor_usage"]
        assert isinstance(family, prometheus_client.core.GaugeMetricFamily)

        self.assertEqual(family.name, "zhmc_pre_processor_usage")
        self.assertEqual(family.documentation, "processor_usage description")
        self.assertEqual(family.type, "gauge")
        sample1 = prometheus_client.samples.Sample(
            name='zhmc_pre_processor_usage',
            labels={'resource': 'cpc_1', 'label1': 'value1'},
            value=0.01)
        self.assertEqual(family.samples, [sample1])

        # pylint: disable=protected-access
        self.assertEqual(set(family._labelnames), {"label1", "resource"})

        families = zhmc_prometheus_exporter.build_family_objects_res(
            resources, yaml_metric_groups, yaml_metrics,
            extra_labels, hmc_version, hmc_api_version, hmc_features,
            se_versions_by_cpc, se_features_by_cpc, session)

        assert len(families) == 1
        assert "zhmc_foo_name" in families
        family = families["zhmc_foo_name"]
        assert isinstance(family, prometheus_client.core.GaugeMetricFamily)

        self.assertEqual(family.name, "zhmc_foo_name")
        self.assertEqual(family.documentation, "CPC name")
        self.assertEqual(family.type, "gauge")
        sample1 = prometheus_client.samples.Sample(
            name='zhmc_foo_name',
            labels={'resource': 'cpc_1', 'label1': 'value1'},
            value='cpc_1')
        self.assertEqual(family.samples, [sample1])

        # pylint: disable=protected-access
        self.assertEqual(set(family._labelnames), {"label1", "resource"})

        teardown_metrics_context(context)


class TestInitZHMCUsageCollector(unittest.TestCase):
    """Tests ZHMCUsageCollector."""

    def test_init(self):
        """Tests ZHMCUsageCollector.__init__."""

        hmc_version = '2.15.0'
        hmc_api_version = (3, 13)
        hmc_features = []
        se_versions_by_cpc = {'cpc_1': '2.15.0'}
        se_features_by_cpc = {'cpc_1': []}

        session = setup_faked_session()
        config_dict = {
            "hmcs": [
                {"host": "192.168.0.0", "userid": "user", "password": "pwd"}
            ],
            "metric_groups": {
                "dpm-system-usage-overview": {"export": True},
            }
        }
        yaml_metric_groups = {
            "dpm-system-usage-overview": {"prefix": "pre"},
        }
        context, resources, _ = \
            zhmc_prometheus_exporter.create_metrics_context(
                session, config_dict, yaml_metric_groups, hmc_version,
                hmc_api_version, hmc_features)
        yaml_metrics = {
            "dpm-system-usage-overview": {
                "processor-usage": {
                    "percent": True,
                    "exporter_name": "processor_usage",
                    "exporter_desc": "processor_usage description"
                }
            }
        }
        yaml_fetch_properties = {
            "cpc": [
                {"property_name": "processor-count-spare"},
            ],
        }
        extra_labels = {}

        my_zhmc_usage_collector = zhmc_prometheus_exporter.ZHMCUsageCollector(
            config_dict, session, context, resources, yaml_metric_groups,
            yaml_metrics, yaml_fetch_properties, extra_labels, "filename",
            "filename", None, None, hmc_version, hmc_api_version, hmc_features,
            se_versions_by_cpc, se_features_by_cpc)
        self.assertEqual(my_zhmc_usage_collector.config_dict, config_dict)
        self.assertEqual(my_zhmc_usage_collector.session, session)
        self.assertEqual(my_zhmc_usage_collector.context, context)
        self.assertEqual(my_zhmc_usage_collector.yaml_metric_groups,
                         yaml_metric_groups)
        self.assertEqual(my_zhmc_usage_collector.yaml_metrics, yaml_metrics)
        self.assertEqual(my_zhmc_usage_collector.metrics_filename, "filename")
        self.assertEqual(my_zhmc_usage_collector.config_filename, "filename")

    def test_collect(self):
        """Test ZHMCUsageCollector.collect"""

        hmc_version = '2.15.0'
        hmc_api_version = (3, 13)
        hmc_features = []
        se_versions_by_cpc = {'cpc_1': '2.15.0'}
        se_features_by_cpc = {'cpc_1': []}

        session = setup_faked_session()
        config_dict = {
            "hmcs": [
                {"host": "192.168.0.0", "userid": "user", "password": "pwd"}
            ],
            "metric_groups": {
                "dpm-system-usage-overview": {"export": True},
            }
        }
        yaml_metric_groups = {
            "dpm-system-usage-overview": {"prefix": "pre"},
        }
        context, resources, _ = \
            zhmc_prometheus_exporter.create_metrics_context(
                session, config_dict, yaml_metric_groups, hmc_version,
                hmc_api_version, hmc_features)
        yaml_metrics = {
            "dpm-system-usage-overview": {
                "processor-usage": {
                    "percent": True,
                    "exporter_name": "processor_usage",
                    "exporter_desc": "processor_usage description"
                }
            }
        }
        yaml_fetch_properties = {
            "cpc": [
                {"property_name": "processor-count-spare"},
            ],
        }
        extra_labels = {}

        my_zhmc_usage_collector = zhmc_prometheus_exporter.ZHMCUsageCollector(
            config_dict, session, context, resources, yaml_metric_groups,
            yaml_metrics, yaml_fetch_properties, extra_labels, "filename",
            "filename", None, None, hmc_version, hmc_api_version, hmc_features,
            se_versions_by_cpc, se_features_by_cpc)
        collected = list(my_zhmc_usage_collector.collect())
        self.assertEqual(len(collected), 1)
        self.assertEqual(type(collected[0]),
                         prometheus_client.core.GaugeMetricFamily)
        self.assertEqual(collected[0].name, "zhmc_pre_processor_usage")
        self.assertEqual(collected[0].documentation,
                         "processor_usage description")
        self.assertEqual(collected[0].type, "gauge")
        sample1 = prometheus_client.samples.Sample(
            name='zhmc_pre_processor_usage',
            labels={'resource': 'cpc_1'}, value=0.01)
        self.assertEqual(collected[0].samples, [sample1])
        # pylint: disable=protected-access
        self.assertEqual(collected[0]._labelnames, ("resource",))


class TestResourceStr(unittest.TestCase):
    """Tests resource_str()."""

    def test_resource_str(self):
        # pylint: disable=no-self-use
        """Tests resource_str()."""

        session = setup_faked_session()
        client = zhmcclient.Client(session)
        cpc1 = client.cpcs.list(
            full_properties=True, filter_args={'name': 'cpc_1'})[0]

        rs_cpc1 = zhmc_prometheus_exporter.resource_str(cpc1)

        assert rs_cpc1 == "CPC 'cpc_1'"


if __name__ == "__main__":
    unittest.main()
