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

import time
import datetime
import hashlib
import os
import sys
import stat
import unittest
import pytest
import zhmcclient
import zhmcclient_mock
import prometheus_client

import zhmc_prometheus_exporter


class TestParseArgs(unittest.TestCase):
    """Tests parse_args."""

    def test_args_store(self):
        """Tests generic input."""
        args = (zhmc_prometheus_exporter.
                parse_args(["-p", "1", "-c", "2", "-m", "3"]))
        self.assertEqual(args.p, "1")
        self.assertEqual(args.c, "2")
        self.assertEqual(args.m, "3")

    def test_default_args(self):
        """Tests for all defaults."""
        args = zhmc_prometheus_exporter.zhmc_prometheus_exporter.parse_args([])
        self.assertEqual(args.p, "9291")
        self.assertEqual(args.c, "/etc/zhmc-prometheus-exporter/hmccreds.yaml")
        self.assertEqual(args.m, "/etc/zhmc-prometheus-exporter/metrics.yaml")


class TestParseYaml(unittest.TestCase):
    """Tests parse_yaml_file."""

    def test_normal_input(self):
        """Tests if some generic file is correctly parsed."""
        # Get a SHA256 of Unixtime to create a filename that does not exist
        filename = str(hashlib.sha256(str(time.time()).encode("utf-8")).
                       hexdigest())
        with open(filename, "w+") as testfile:
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
        with open(filename, "w+"):
            pass
        # Make it unreadable (mode 000)
        os.chmod(filename, not stat.S_IRWXU)
        with self.assertRaises(PermissionError):
            (zhmc_prometheus_exporter.
             parse_yaml_file(filename, 'test file'))
        os.remove(filename)

    def test_not_found_error(self):
        """Tests if file not found is correctly handled."""
        filename = str(hashlib.sha256(str(time.time()).encode("utf-8")).
                       hexdigest())
        with self.assertRaises(FileNotFoundError):
            zhmc_prometheus_exporter.parse_yaml_file(filename, 'test file')


class TestParseSections(unittest.TestCase):
    """Tests parse_yaml_sections."""

    def test_normal_input(self):
        """Tests with some generic input."""
        sample_dict = {"hmc": "127.0.0.1", "userid": "user", "password": "pwd"}
        sample_dict_wrap = {"metrics": sample_dict}
        cred_dict = (zhmc_prometheus_exporter.
                     parse_yaml_sections(sample_dict_wrap,
                                         ("metrics",),
                                         "filename")[0])
        self.assertEqual(cred_dict, sample_dict)

    def test_section_error(self):
        """Tests for a missing section."""
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            (zhmc_prometheus_exporter.
             parse_yaml_sections({}, ("metrics",), "filename"))

    def test_attribute_error(self):
        """Tests for something that is not YAML."""
        with self.assertRaises(AttributeError):
            (zhmc_prometheus_exporter.
             parse_yaml_sections("notyaml", ("metrics",), "filename"))


class TestCheckCreds(unittest.TestCase):
    """Tests check_creds_yaml."""

    def test_check_creds_yaml(self):
        """Tests all sorts of missing, incorrect, and correct information."""
        missing_hmc = {"userid": "user", "password": "pwd"}
        incorrect_ip = {"hmc": "256.0.0.1",
                        "userid": "user",
                        "password": "pwd"}
        missing_user = {"hmc": "127.0.0.1", "password": "pwd"}
        missing_pwd = {"hmc": "127.0.0.1", "userid": "user"}
        correct = {"hmc": "127.0.0.1", "userid": "user", "password": "pwd"}
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            zhmc_prometheus_exporter.check_creds_yaml(missing_hmc, "filename")
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            zhmc_prometheus_exporter.check_creds_yaml(incorrect_ip, "filename")
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            zhmc_prometheus_exporter.check_creds_yaml(missing_user, "filename")
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            zhmc_prometheus_exporter.check_creds_yaml(missing_pwd, "filename")
        zhmc_prometheus_exporter.check_creds_yaml(correct, "filename")


class TestCheckMetrics(unittest.TestCase):
    """Tests check_metrics_yaml."""

    def test_check_metrics_yaml(self):
        """Tests all sorts of missing, incorrect, and correct information."""
        bad_prefix = {"metric_group": {"fetch": True}}
        bad_fetch = {"metric_group": {"prefix": "pre"}}
        bad_fetch_format = {"metric_group": {"prefix": "pre",
                                             "fetch": "none"}}
        correct_groups = {"metric_group": {"prefix": "pre", "fetch": True}}
        bad_percent = {"metric_group": {"metric": {"exporter_name": "name",
                                                   "exporter_desc": "desc"}}}
        bad_percent_format = {"metric_group": {"metric": {
            "percent": "none",
            "exporter_name": "name",
            "exporter_desc": "desc"}}}
        bad_name = {"metric_group": {"metric": {"percent": True,
                                                "exporter_desc": "desc"}}}
        bad_desc = {"metric_group": {"metric": {"percent": True,
                                                "exporter_name": "name"}}}
        correct_metric = {"metric_group": {"metric": {
            "percent": True,
            "exporter_name": "name",
            "exporter_desc": "desc"}}}
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            (zhmc_prometheus_exporter.
             check_metrics_yaml(bad_prefix, correct_metric, "filename"))
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            (zhmc_prometheus_exporter.
             check_metrics_yaml(bad_fetch, correct_metric, "filename"))
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            (zhmc_prometheus_exporter.
             check_metrics_yaml(bad_fetch_format, correct_metric, "filename"))
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            (zhmc_prometheus_exporter.
             check_metrics_yaml({}, correct_metric, "filename"))
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            (zhmc_prometheus_exporter.
             check_metrics_yaml(correct_groups, bad_percent, "filename"))
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            zhmc_prometheus_exporter.check_metrics_yaml(correct_groups,
                                                        bad_percent_format,
                                                        "filename")
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            (zhmc_prometheus_exporter.
             check_metrics_yaml(correct_groups, bad_name, "filename"))
        with self.assertRaises(zhmc_prometheus_exporter.YAMLInfoNotFoundError):
            (zhmc_prometheus_exporter.
             check_metrics_yaml(correct_groups, bad_desc, "filename"))
        (zhmc_prometheus_exporter.
         check_metrics_yaml(correct_groups, correct_metric, "filename"))


# Fake HMC derived from
# github.com/zhmcclient/python-zhmcclient/zhmcclient_mock/_hmc.py
class TestCreateContext(unittest.TestCase):
    """Tests create_metrics_context with a fake HMC."""

    def test_normal_input(self):
        """Tests normal input with a generic metric group."""
        session = zhmcclient_mock.FakedSession("fake-host", "fake-hmc",
                                               "2.13.1", "1.8")
        context = zhmc_prometheus_exporter.create_metrics_context(
            session,
            {"dpm-system-usage-overview": {"prefix": "pre", "fetch": True}},
            "filename")
        # pylint: disable=protected-access
        self.assertEqual(type(context), zhmcclient._metrics.MetricsContext)
        context.delete()
        session.logoff()

    def test_timeout(self):
        """Tests a timeout with an IP where no HMC is sitting.
        Omitting this test improves test time by three orders of magnitude.
        """
        cred_dict = {"hmc": "192.168.0.0", "userid": "user", "password": "pwd"}
        session = zhmc_prometheus_exporter.create_session(cred_dict)
        with self.assertRaises(zhmc_prometheus_exporter.ConnectionError):
            zhmc_prometheus_exporter.create_metrics_context(
                session, {}, "filename")


class TestDeleteContext(unittest.TestCase):
    """Tests delete_metrics_context."""

    def test_delete_context(self):
        # pylint: disable=no-self-use
        """Tests normal input, just needs to know no errors happen."""
        session = zhmcclient_mock.FakedSession("fake-host", "fake-hmc",
                                               "2.13.1", "1.8")
        client = zhmcclient.Client(session)
        context = client.metrics_contexts.create(
            {"anticipated-frequency-seconds": 15,
             "metric-groups": ["dpm-system-usage-overview"]})
        zhmc_prometheus_exporter.delete_metrics_context(session, context)


def setup_faked_session():
    """Create a faked session."""

    session = zhmcclient_mock.FakedSession("fake-host", "fake-hmc",
                                           "2.13.1", "1.8")
    session.hmc.add_resources({"cpcs": [{"properties": {
        "name": "cpc_1", "object-uri": "cpc_1"}}]})
    session.hmc.metrics_contexts.add_metric_group_definition(
        zhmcclient_mock.FakedMetricGroupDefinition(
            name="dpm-system-usage-overview",
            types=[("metric-1", "integer-metric")]))
    session.hmc.metrics_contexts.add_metric_values(
        zhmcclient_mock.FakedMetricObjectValues(
            group_name="dpm-system-usage-overview",
            resource_uri="cpc_1",
            timestamp=datetime.datetime.now(),
            values=[("metric-1", 1)]))
    return session


def setup_metrics_context():
    """Create a faked session and return a faked metrics context."""

    session = setup_faked_session()
    client = zhmcclient.Client(session)
    context = client.metrics_contexts.create(
        {"anticipated-frequency-seconds": 15,
         "metric-groups": ["dpm-system-usage-overview"]})
    return context


def teardown_metrics_context(context):
    """Delete a faked metrics context."""
    context.delete()


class TestMetrics(unittest.TestCase):
    """Tests metrics."""

    def test_retrieve_metrics(self):
        # pylint: disable=no-self-use
        """Tests retrieve_metrics()"""

        context = setup_metrics_context()

        metrics_object = zhmc_prometheus_exporter.retrieve_metrics(context)

        assert isinstance(metrics_object, zhmcclient.MetricsResponse)
        assert len(metrics_object.metric_group_values) == 1
        mgv = metrics_object.metric_group_values[0]
        assert mgv.name == 'dpm-system-usage-overview'
        assert len(mgv.object_values) == 1
        ov = mgv.object_values[0]
        assert ov.resource.name == 'cpc_1'
        assert ov.metrics == {'metric-1': 1}

        teardown_metrics_context(context)

    def test_build_family_objects(self):
        """Tests build_family_objects()"""

        yaml_metric_groups = {
            "dpm-system-usage-overview": {
                "prefix": "pre",
                "fetch": True,
            }
        }
        yaml_metrics = {
            "dpm-system-usage-overview": {
                "metric-1": {
                    "percent": True,
                    "exporter_name": "metric1",
                    "exporter_desc": "metric1 description",
                }
            }
        }

        context = setup_metrics_context()
        metrics_object = zhmc_prometheus_exporter.retrieve_metrics(context)

        families = zhmc_prometheus_exporter.build_family_objects(
            metrics_object, yaml_metric_groups, yaml_metrics, 'file')

        assert len(families) == 1
        assert "zhmc_pre_metric1" in families
        family = families["zhmc_pre_metric1"]
        assert isinstance(family, prometheus_client.core.GaugeMetricFamily)

        self.assertEqual(family.name, "zhmc_pre_metric1")
        self.assertEqual(family.documentation, "metric1 description")
        self.assertEqual(family.type, "gauge")
        sample1 = prometheus_client.samples.Sample(
            name='zhmc_pre_metric1', labels={'resource': 'cpc_1'}, value=0.01)
        self.assertEqual(family.samples, [sample1])

        # pylint: disable=protected-access
        self.assertEqual(family._labelnames, ("resource",))

        teardown_metrics_context(context)


class TestInitZHMCUsageCollector(unittest.TestCase):
    """Tests ZHMCUsageCollector."""

    def test_init(self):
        """Tests ZHMCUsageCollector.__init__."""

        cred_dict = {"hmc": "192.168.0.0", "userid": "user", "password": "pwd"}
        session = setup_faked_session()
        yaml_metric_groups = {"dpm-system-usage-overview": {"prefix": "pre",
                                                            "fetch": True}}
        context = zhmc_prometheus_exporter.create_metrics_context(
            session, yaml_metric_groups, "filename")
        yaml_metrics = {"dpm-system-usage-overview": {"metric-1": {
            "percent": True,
            "exporter_name": "metric1",
            "exporter_desc": "metric1 description"}}}
        my_zhmc_usage_collector = zhmc_prometheus_exporter.ZHMCUsageCollector(
            cred_dict, session, context, yaml_metric_groups, yaml_metrics,
            "filename", "filename")
        self.assertEqual(my_zhmc_usage_collector.yaml_creds, cred_dict)
        self.assertEqual(my_zhmc_usage_collector.session, session)
        self.assertEqual(my_zhmc_usage_collector.context, context)
        self.assertEqual(my_zhmc_usage_collector.yaml_metric_groups,
                         yaml_metric_groups)
        self.assertEqual(my_zhmc_usage_collector.yaml_metrics, yaml_metrics)
        self.assertEqual(my_zhmc_usage_collector.filename_metrics, "filename")
        self.assertEqual(my_zhmc_usage_collector.filename_creds, "filename")

    def test_collect(self):
        """Test ZHMCUsageCollector.collect"""

        cred_dict = {"hmc": "192.168.0.0", "userid": "user", "password": "pwd"}
        session = setup_faked_session()
        yaml_metric_groups = {"dpm-system-usage-overview": {"prefix": "pre",
                                                            "fetch": True}}
        context = zhmc_prometheus_exporter.create_metrics_context(
            session, yaml_metric_groups, "filename")
        yaml_metrics = {"dpm-system-usage-overview": {"metric-1": {
            "percent": True,
            "exporter_name": "metric1",
            "exporter_desc": "metric1 description"}}}
        my_zhmc_usage_collector = zhmc_prometheus_exporter.ZHMCUsageCollector(
            cred_dict, session, context, yaml_metric_groups, yaml_metrics,
            "filename", "filename")
        collected = list(my_zhmc_usage_collector.collect())
        self.assertEqual(len(collected), 1)
        self.assertEqual(type(collected[0]),
                         prometheus_client.core.GaugeMetricFamily)
        self.assertEqual(collected[0].name, "zhmc_pre_metric1")
        self.assertEqual(collected[0].documentation, "metric1 description")
        self.assertEqual(collected[0].type, "gauge")
        sample1 = prometheus_client.samples.Sample(
            name='zhmc_pre_metric1', labels={'resource': 'cpc_1'}, value=0.01)
        self.assertEqual(collected[0].samples, [sample1])
        # pylint: disable=protected-access
        self.assertEqual(collected[0]._labelnames, ("resource",))


if __name__ == "__main__":
    unittest.main()
