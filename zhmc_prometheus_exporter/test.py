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
import stat

from io import StringIO
import unittest
from unittest.mock import patch

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
        # Get a SHA1 of Unixtime to create a filename that does not exist
        filename = str(hashlib.sha1(str(time.time()).encode("utf-8")).
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
        self.assertEqual(zhmc_prometheus_exporter.parse_yaml_file(filename),
                         expected_dict)
        os.remove(filename)

    def test_permission_error(self):
        """Tests if permission denied is correctly handled."""
        filename = str(hashlib.sha1(str(time.time()).encode("utf-8")).
                       hexdigest())
        with open(filename, "w+"):
            pass
        # Make it unreadable (mode 000)
        os.chmod(filename, not stat.S_IRWXU)
        with self.assertRaises(PermissionError):
            (zhmc_prometheus_exporter.
             parse_yaml_file(filename))
        os.remove(filename)

    def test_not_found_error(self):
        """Tests if file not found is correctly handled."""
        filename = str(hashlib.sha1(str(time.time()).encode("utf-8")).
                       hexdigest())
        with self.assertRaises(FileNotFoundError):
            zhmc_prometheus_exporter.parse_yaml_file(filename)


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
        context = (zhmc_prometheus_exporter.
                   create_metrics_context(session,
                                          {"metric-group": {"prefix": "pre",
                                                            "fetch": True}},
                                          "filename"))
        self.assertEqual(type(context), zhmcclient._metrics.MetricsContext)
        context.delete()
        session.logoff()

    def test_timeout(self):
        """Tests a timeout with an IP where no HMC is sitting.
        Omitting this test improves test time by three orders of magnitude.
        """
        cred_dict = {"hmc": "192.168.0.0", "userid": "user", "password": "pwd"}
        session = zhmc_prometheus_exporter.create_session(cred_dict)
        with self.assertRaises(zhmc_prometheus_exporter.ConnectTimeout):
            (zhmc_prometheus_exporter.
             create_metrics_context(session, {}, "filename"))


class TestDeleteContext(unittest.TestCase):
    """Tests delete_metrics_context."""

    def test_delete_context(self):
        """Tests normal input, just needs to know no errors happen."""
        session = zhmcclient_mock.FakedSession("fake-host", "fake-hmc",
                                               "2.13.1", "1.8")
        client = zhmcclient.Client(session)
        context = client.metrics_contexts.create(
            {"anticipated-frequency-seconds": 15,
             "metric-groups": ["metric-group"]})
        zhmc_prometheus_exporter.delete_metrics_context(session, context)


class TestRetrieveMetrics(unittest.TestCase):
    """Tests retrieve_metrics."""

    def test_retrieve_metrics(self):
        """Tests metrics retrieval with a fake CPC and fake metrics."""
        session = zhmcclient_mock.FakedSession("fake-host", "fake-hmc",
                                               "2.13.1", "1.8")
        session.hmc.add_resources({"cpcs": [{"properties": {
            "name": "cpc_1", "object-uri": "cpc_1"}}]})
        session.hmc.metrics_contexts.add_metric_group_definition(
            zhmcclient_mock.FakedMetricGroupDefinition(
                name="dpm-system-usage-overview",
                types=[("metric", "integer-metric")]))
        session.hmc.metrics_contexts.add_metric_values(
            zhmcclient_mock.FakedMetricObjectValues(
                group_name="dpm-system-usage-overview",
                resource_uri="cpc_1",
                timestamp=datetime.datetime.now(),
                values=[("metric", 1)]))
        client = zhmcclient.Client(session)
        context = client.metrics_contexts.create(
            {"anticipated-frequency-seconds": 15,
             "metric-groups": ["dpm-system-usage-overview"]})
        expected_output = {"dpm-system-usage-"
                           "overview": {"cpc_1": {"metric": 1}}}
        actual_output = zhmc_prometheus_exporter.retrieve_metrics(context)
        self.assertEqual(expected_output, actual_output)
        context.delete()
        session.logoff()


class TestFormatUnknown(unittest.TestCase):
    """Tests format_unknown_metrics."""

    def test_non_percent(self):
        """Tests one with a non-percent value."""
        expected_output = {"percent": False,
                           "exporter_name": "my_metric",
                           "exporter_desc": "my metric"}
        actual_output = (zhmc_prometheus_exporter.
                         format_unknown_metric("my-metric"))
        self.assertEqual(expected_output, actual_output)

    def test_percent(self):
        """Tests one with a percent value."""
        expected_output = {"percent": True,
                           "exporter_name": "my_metric_usage_ratio",
                           "exporter_desc": "my metric usage"}
        actual_output = (zhmc_prometheus_exporter.
                         format_unknown_metric("my-metric-usage"))
        self.assertEqual(expected_output, actual_output)


class TestIdentifyIncoming(unittest.TestCase):
    """Tests identify_incoming_metrics."""

    def test_unexpected_metric(self):
        """Tests with some metric that is not known."""
        # Verify a known metric does not get modified
        incoming_metrics = {"metric-group": {"resource": {
            "known-metric": 0, "unknown-metric": 0}}}
        yaml_metrics = {"metric-group": {"known-metric": {
            "percent": False,
            "exporter_name": "known_metric",
            "exporter_desc": "known metric"}}}
        expected_output = {"metric-group": {
            "known-metric": {
                "percent": False,
                "exporter_name": "known_metric",
                "exporter_desc": "known metric"},
            "unknown-metric": {
                "percent": False,
                "exporter_name": "unknown_metric",
                "exporter_desc": "unknown metric"}}}
        # Ignore warning
        with patch("sys.stderr", new=StringIO()):
            actual_output = (zhmc_prometheus_exporter.
                             identify_incoming_metrics(incoming_metrics,
                                                       yaml_metrics,
                                                       "filename"))
        self.assertEqual(expected_output, actual_output)


class TestAddFamilies(unittest.TestCase):
    """Tests add_families."""

    def test_add_families(self):
        """Tests with some generic input."""
        yaml_metric_groups = {"metric-group": {"prefix": "pre",
                                               "fetch": True}}
        input_metrics = {"metric-group": {"metric": {
            "percent": True,
            "exporter_name": "metric",
            "exporter_desc": "metric"}}}
        output = (zhmc_prometheus_exporter.
                  add_families(yaml_metric_groups, input_metrics))
        families = output["metric-group"]["metric"]
        self.assertIsInstance(families,
                              prometheus_client.core.GaugeMetricFamily)
        self.assertEqual(families.name, "zhmc_pre_metric")
        self.assertEqual(families.documentation, "metric")
        self.assertEqual(families.type, "gauge")
        self.assertEqual(families.samples, [])
        self.assertEqual(families._labelnames, ("resource",))


class TestStoreMetrics(unittest.TestCase):
    """Tests store_metrics."""

    def test_store_metrics(self):
        """Tests with some generic input."""
        yaml_metric_groups = {"metric-group": {"prefix": "pre",
                                               "fetch": True}}
        yaml_metrics = {"metric-group": {"metric": {
            "percent": True,
            "exporter_name": "metric",
            "exporter_desc": "metric"}}}
        yaml_metrics_dict = {"metric-group": {"resource": {"metric": 0}}}
        family_objects = (zhmc_prometheus_exporter.
                          add_families(yaml_metric_groups, yaml_metrics))
        output = zhmc_prometheus_exporter.store_metrics(yaml_metrics_dict,
                                                        yaml_metrics,
                                                        family_objects)
        stored = output["metric-group"]["metric"]
        self.assertIsInstance(stored, prometheus_client.core.GaugeMetricFamily)
        self.assertEqual(stored.name, "zhmc_pre_metric")
        self.assertEqual(stored.documentation, "metric")
        self.assertEqual(stored.type, "gauge")
#        self.assertEqual(stored.samples, [("zhmc_pre_metric",
#                                           {"resource": "resource"},
#                                           0)])
        self.assertEqual(stored._labelnames, ("resource",))


class TestInitZHMCUsageCollector(unittest.TestCase):
    """Tests ZHMCUsageCollector."""

    def test_init(self):
        """Tests ZHMCUsageCollector.__init__."""
        cred_dict = {"hmc": "192.168.0.0", "userid": "user", "password": "pwd"}
        session = zhmcclient_mock.FakedSession("fake-host", "fake-hmc",
                                               "2.13.1", "1.8")
        yaml_metric_groups = {"metric-group": {"prefix": "pre",
                                               "fetch": True}}
        context = (zhmc_prometheus_exporter.
                   create_metrics_context(session,
                                          yaml_metric_groups,
                                          "filename"))
        yaml_metrics = {"metric-group": {"metric": {
            "percent": True,
            "exporter_name": "metric",
            "exporter_desc": "metric"}}}
        my_zhmc_usage_collector = (zhmc_prometheus_exporter.
                                   ZHMCUsageCollector(cred_dict,
                                                      session,
                                                      context,
                                                      yaml_metric_groups,
                                                      yaml_metrics,
                                                      "filename",
                                                      "filename"))
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
        session = zhmcclient_mock.FakedSession("fake-host", "fake-hmc",
                                               "2.13.1", "1.8")
        yaml_metric_groups = {"metric-group": {"prefix": "pre",
                                               "fetch": True}}
        context = (zhmc_prometheus_exporter.
                   create_metrics_context(session,
                                          yaml_metric_groups,
                                          "filename"))
        yaml_metrics = {"metric-group": {"metric": {
            "percent": True,
            "exporter_name": "metric",
            "exporter_desc": "metric"}}}
        my_zhmc_usage_collector = (zhmc_prometheus_exporter.
                                   ZHMCUsageCollector(cred_dict,
                                                      session,
                                                      context,
                                                      yaml_metric_groups,
                                                      yaml_metrics,
                                                      "filename",
                                                      "filename"))
        collected = list(my_zhmc_usage_collector.collect())
        self.assertEqual(len(collected), 1)
        self.assertEqual(type(collected[0]),
                         prometheus_client.core.GaugeMetricFamily)
        self.assertEqual(collected[0].name, "zhmc_pre_metric")
        self.assertEqual(collected[0].documentation, "metric")
        self.assertEqual(collected[0].type, "gauge")
        self.assertEqual(collected[0].samples, [])
        self.assertEqual(collected[0]._labelnames, ("resource",))


if __name__ == "__main__":
    unittest.main()
