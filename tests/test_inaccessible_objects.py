# Copyright 2025 IBM Corp. All Rights Reserved.
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
Unit tests for the handling of objects without object access permission.

The HMC behaves as if objects without object access permission did not exist:
They are not returned in list operations, and a "Get Properties" operation on
them fails with HTTP status 404.1. However, URIs of such objects may still be
returned in the metrics service or in properties of other objects, and objects
may be accessible while their parent object is not.

These tests set up faked HMCs in which the inaccessible objects either do not
exist (which is what the faked HMC returns for them: 404.1), or are accessible
but have an inaccessible parent (simulated by making the Get operation on the
parent fail with 404.1).
"""

import datetime
import os

import pytest  # pylint: disable=import-error
import zhmcclient  # pylint: disable=import-error,wrong-import-order
import zhmcclient_mock  # pylint: disable=import-error,wrong-import-order

from zhmc_prometheus_exporter import zhmc_prometheus_exporter as exporter
from zhmc_prometheus_exporter._resource_cache import ResourceCache

HMC_VERSION = (2, 15, 0)
HMC_API_VERSION = (4, 1)
HMC_FEATURES = []

METRICS_FILE = os.path.join(
    os.path.dirname(exporter.__file__), 'data', 'metrics.yaml')

CPC1_URI = '/api/cpcs/c0c1'
CPC2_URI = '/api/cpcs/c0c2'  # Inaccessible CPC
PART1_URI = '/api/partitions/ba01'
PART2_URI = '/api/partitions/ba02'  # Inaccessible partition
PART3_URI = '/api/partitions/ba03'  # Accessible, but CPC2 inaccessible
AD1_URI = '/api/adapters/ad01'
AD2_URI = '/api/adapters/ad02'  # Inaccessible adapter
AD3_URI = '/api/adapters/ad03'  # Accessible, but CPC2 inaccessible


def load_yaml():
    """Return the metric groups and metrics of the metrics definition file"""
    content = exporter.parse_yaml_file(
        METRICS_FILE, 'metric definition file', 'metrics_schema.yaml')
    return content['metric_groups'], content['metrics']


def metric_values(session, group_name, resource_uri, values):
    """
    Return a faked metric object values object. All metrics of the metric
    group are provided; those not specified in `values` get a default value.
    The metric definitions are taken from the faked HMC.
    """
    client = zhmcclient.Client(session)
    context = client.metrics_contexts.create(
        {"anticipated-frequency-seconds": 15,
         "metric-groups": [group_name]})
    mg_def = context.metric_group_definitions[group_name]
    context.delete()
    value_dict = dict(values)
    all_values = []
    for m_def in mg_def.metric_definitions.values():
        if m_def.name in value_dict:
            m_value = value_dict[m_def.name]
        elif m_def.type is str:
            m_value = 'x'
        else:
            m_value = 1
        all_values.append((m_def.name, m_value))
    return zhmcclient_mock.FakedMetricObjectValues(
        group_name=group_name,
        resource_uri=resource_uri,
        timestamp=datetime.datetime.now(),
        values=all_values)


def make_session(partitions=True, adapters=True):
    """
    Return a faked session for a faked HMC with CPC1 (DPM mode), partition
    ba01 and adapter ad1. Objects ba02, ad2 and CPC2 are not defined, and are
    thus inaccessible.
    """
    session = zhmcclient_mock.FakedSession(
        "fake-host", "fake-hmc", "2.15.0", "4.1")
    session.hmc.consoles.add({
        'object-id': None,
        'name': 'fake-console1',
        'class': 'console',
    })
    cpc = session.hmc.cpcs.add({
        'object-id': 'c0c1',
        'name': 'cpc_1',
        'dpm-enabled': True,
        'se-version': '2.15.0',
    })
    if partitions:
        cpc.partitions.add({
            'object-id': 'ba01',
            'name': 'part_1',
            'status': 'active',
        })
    if adapters:
        cpc.adapters.add({
            'object-id': 'ad01',
            'name': 'ad_1',
            'type': 'osd',
            'adapter-family': 'osa',
            'status': 'active',
        })
    return session


def hide_parent(session, hidden_uri, parents):
    """
    Make the faked session behave as if the parent CPC of some objects was
    inaccessible: The "Get Properties" operation on the objects in `parents`
    returns the properties with the parent set to the URI hidden_uri (which
    fails with 404.1 because it is not defined in the faked HMC).

    Returns the original get() method.
    """
    orig_get = session.get

    def get(uri, *args, **kwargs):
        base_uri = uri.split('?')[0]
        if base_uri in parents:
            return {
                'object-uri': base_uri,
                'name': parents[base_uri],
                'parent': hidden_uri,
                'status': 'active',
            }
        return orig_get(uri, *args, **kwargs)

    session.get = get
    return orig_get


def run_collection(session, mg_names, target_all=True):
    """
    Set up the resource cache for the specified metric groups, retrieve the
    metrics, and build the Prometheus family objects, in the same way as the
    exporter does.

    Returns the dict of family objects, with the family objects for
    metric-based and resource-based metric groups combined.
    """
    yaml_metric_groups, yaml_metrics = load_yaml()
    client = zhmcclient.Client(session)
    cpc_list = client.cpcs.list()
    target_cpc_list = cpc_list if target_all else cpc_list[:1]
    se_versions = {c.name: (2, 15, 0) for c in cpc_list}
    se_features = {c.name: [] for c in cpc_list}

    metric_mg_names = [
        n for n in mg_names if yaml_metric_groups[n]['type'] == 'metric']

    cache = ResourceCache(
        client, cpc_list, target_cpc_list, yaml_metric_groups, mg_names,
        se_features)
    cache.setup()

    families = {}
    if metric_mg_names:
        context = client.metrics_contexts.create(
            {"anticipated-frequency-seconds": 15,
             "metric-groups": metric_mg_names})
        metrics_object = exporter.retrieve_metrics(context)
        families.update(exporter.build_family_objects(
            cache, metrics_object, yaml_metric_groups, yaml_metrics, {},
            HMC_VERSION, HMC_API_VERSION, HMC_FEATURES, se_versions,
            se_features))
    families.update(exporter.build_family_objects_res(
        cache, yaml_metric_groups, yaml_metrics, {},
        HMC_VERSION, HMC_API_VERSION, HMC_FEATURES, se_versions,
        se_features))
    return families


def label_sets(families, family_name, keys):
    """
    Return the list of label dicts of the samples of a family, reduced to the
    specified label names.
    """
    return [{k: s.labels[k] for k in keys}
            for s in families[family_name].samples]


def test_partition_metrics_no_part_access():
    """
    No access to some partitions, partition-level HMC metrics are enabled.
    """
    session = make_session()
    session.hmc.add_metric_values(metric_values(
        session, 'partition-usage', PART1_URI, [('processor-usage', 10)]))
    session.hmc.add_metric_values(metric_values(
        session, 'partition-usage', PART2_URI, [('processor-usage', 20)]))

    families = run_collection(session, ['partition-usage'])

    labels = label_sets(
        families, 'zhmc_partition_processor_usage_ratio', ['cpc', 'partition'])
    assert labels == [{'cpc': 'cpc_1', 'partition': 'part_1'}]


def test_partition_resource_no_part_access():
    """
    No access to some partitions, partition-level resource metrics are enabled.
    """
    session = make_session()

    families = run_collection(session, ['partition-resource'])

    labels = label_sets(
        families, 'zhmc_partition_status_int', ['cpc', 'partition'])
    assert labels == [{'cpc': 'cpc_1', 'partition': 'part_1'}]


def test_adapter_metrics_no_adapter_access():
    """
    No access to some adapters, adapter-level HMC metrics are enabled.
    """
    session = make_session()
    session.hmc.add_metric_values(metric_values(
        session, 'adapter-usage', AD1_URI, [('adapter-usage', 10)]))
    session.hmc.add_metric_values(metric_values(
        session, 'adapter-usage', AD2_URI, [('adapter-usage', 20)]))

    families = run_collection(session, ['adapter-usage'])

    labels = label_sets(
        families, 'zhmc_adapter_usage_ratio', ['cpc', 'adapter'])
    assert labels == [{'cpc': 'cpc_1', 'adapter': 'ad_1'}]


def test_adapter_resource_no_adapter_access():
    """
    No access to some adapters, adapter-level resource metrics are enabled.
    """
    session = make_session()

    families = run_collection(session, ['adapter-resource'])

    labels = label_sets(families, 'zhmc_adapter_status_int', ['cpc', 'adapter'])
    assert labels == [{'cpc': 'cpc_1', 'adapter': 'ad_1'}]


def test_port_metrics_no_adapter_access():
    """
    No access to some adapters, port-level HMC metrics are enabled (they use
    the adapter name as a label).
    """
    session = make_session()
    session.hmc.add_metric_values(metric_values(
        session, 'network-physical-adapter-port', AD1_URI,
        [('network-port-id', 0), ('bytes-sent', 10)]))
    session.hmc.add_metric_values(metric_values(
        session, 'network-physical-adapter-port', AD2_URI,
        [('network-port-id', 0), ('bytes-sent', 20)]))

    families = run_collection(
        session, ['network-physical-adapter-port'])

    for family in families.values():
        for labels in [s.labels for s in family.samples]:
            assert labels['adapter'] == 'ad_1'
    assert families


def test_cpc_metrics_no_cpc_access():
    """
    No access to some CPCs, CPC-level HMC metrics are enabled.
    """
    session = make_session()
    session.hmc.add_metric_values(metric_values(
        session, 'dpm-system-usage-overview', CPC1_URI,
        [('processor-usage', 10)]))
    session.hmc.add_metric_values(metric_values(
        session, 'dpm-system-usage-overview', CPC2_URI,
        [('processor-usage', 20)]))

    families = run_collection(session, ['dpm-system-usage-overview'])

    labels = label_sets(families, 'zhmc_cpc_processor_usage_ratio', ['cpc'])
    assert labels == [{'cpc': 'cpc_1'}]


def test_cpc_resource_no_cpc_access():
    """
    No access to some CPCs, CPC-level resource metrics are enabled.
    """
    session = make_session()

    families = run_collection(session, ['cpc-resource'])

    assert families
    for family in families.values():
        for sample in family.samples:
            assert sample.labels['cpc'] == 'cpc_1'


def test_partition_metrics_no_cpc_access():
    """
    No access to some CPCs, partition-level HMC metrics are enabled (they use
    the CPC name as a label). The partition is accessible but its parent CPC
    is not.
    """
    session = make_session()
    hide_parent(session, CPC2_URI, {PART3_URI: 'part_3'})
    session.hmc.add_metric_values(metric_values(
        session, 'partition-usage', PART1_URI, [('processor-usage', 10)]))
    session.hmc.add_metric_values(metric_values(
        session, 'partition-usage', PART3_URI, [('processor-usage', 30)]))

    families = run_collection(session, ['partition-usage'])

    labels = label_sets(
        families, 'zhmc_partition_processor_usage_ratio', ['cpc', 'partition'])
    assert labels == [{'cpc': 'cpc_1', 'partition': 'part_1'}]


def test_adapter_metrics_no_cpc_access():
    """
    No access to the parent CPC of an adapter, adapter-level HMC metrics are
    enabled (issue #757).
    """
    session = make_session()
    hide_parent(session, CPC2_URI, {AD3_URI: 'ad_3'})
    session.hmc.add_metric_values(metric_values(
        session, 'adapter-usage', AD1_URI, [('adapter-usage', 10)]))
    session.hmc.add_metric_values(metric_values(
        session, 'adapter-usage', AD3_URI, [('adapter-usage', 30)]))

    families = run_collection(session, ['adapter-usage'])

    labels = label_sets(
        families, 'zhmc_adapter_usage_ratio', ['cpc', 'adapter'])
    assert labels == [{'cpc': 'cpc_1', 'adapter': 'ad_1'}]


def test_port_metrics_no_cpc_access():
    """
    No access to the parent CPC of an adapter, port-level HMC metrics are
    enabled.
    """
    session = make_session()
    hide_parent(session, CPC2_URI, {AD3_URI: 'ad_3'})
    session.hmc.add_metric_values(metric_values(
        session, 'network-physical-adapter-port', AD3_URI,
        [('network-port-id', 0), ('bytes-sent', 30)]))

    families = run_collection(session, ['network-physical-adapter-port'])

    assert not families


def test_lookup_inaccessible_parent_cpc():
    """
    The cache lookup of partitions, adapters and storage groups whose parent
    CPC is inaccessible returns None and does not fail.
    """
    session = make_session()
    hide_parent(session, CPC2_URI, {
        PART3_URI: 'part_3',
        AD3_URI: 'ad_3',
    })
    yaml_metric_groups, _ = load_yaml()
    client = zhmcclient.Client(session)
    cpc_list = client.cpcs.list()
    cache = ResourceCache(
        client, cpc_list, cpc_list, yaml_metric_groups,
        ['partition-usage'], {'cpc_1': []})
    cache.setup()

    assert cache.lookup(PART3_URI) is None
    assert cache.lookup(AD3_URI) is None
    assert cache.lookup(CPC2_URI) is None
    assert cache.lookup(PART2_URI) is None
    assert cache.lookup(AD2_URI) is None
    # Second lookup is served from the cache
    assert cache.lookup(PART3_URI) is None
    assert not cache.is_for_target_cpc(cache.lookup(PART3_URI))


@pytest.mark.parametrize(
    "target_all", [True, False]
)
def test_no_partitions_listed(target_all):
    """
    No access to any partitions or adapters: No metrics but no failure either.
    """
    session = make_session(partitions=False, adapters=False)
    session.hmc.add_metric_values(metric_values(
        session, 'partition-usage', PART1_URI, [('processor-usage', 10)]))

    families = run_collection(
        session, ['partition-usage', 'partition-resource', 'adapter-resource'],
        target_all)

    assert not families
