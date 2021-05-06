.. Copyright 2018 IBM Corp. All Rights Reserved.
..
.. Licensed under the Apache License, Version 2.0 (the "License");
.. you may not use this file except in compliance with the License.
.. You may obtain a copy of the License at
..
..    http://www.apache.org/licenses/LICENSE-2.0
..
.. Unless required by applicable law or agreed to in writing, software
.. distributed under the License is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.

Usage
=====

This section describes how to use the exporter beyond the quick introduction
in :ref:`Quickstart`.

Running on a system
-------------------

If you want to run the exporter on some system (e.g. on your workstation for
trying it out), it is recommended to use a virtual Python environment.

With the virtual Python environment active, follow the steps in
:ref:`Quickstart` to install, establish the required files, and to run the
exporter.

Running in a Docker container
-----------------------------

If you want to run the exporter in a Docker container you can create the
container as follows, using the ``Dockerfile`` provided in the Git repository.

* Clone the Git repository of the exporter and switch to the clone's root
  directory:

  .. code-block:: bash

      $ git clone https://github.com/zhmcclient/zhmc-prometheus-exporter
      $ cd zhmc-prometheus-exporter

* Provide an HMC credentials file named ``hmccreds.yaml`` in the clone's root
  directory, as described in :ref:`Quickstart`. You can copy it from the
  ``examples`` directory.

* Provide a metric definition file named ``metrics.yaml`` in the clone's root
  directory, as described in :ref:`Quickstart`. You can copy it from the
  ``examples`` directory.

* Build the container as follows:

  .. code-block:: bash

      $ docker build . -t zhmcexporter

* Run the container as follows:

  .. code-block:: bash

      $ docker run -p 9291:9291 zhmcexporter

zhmc_prometheus_exporter command
--------------------------------

The ``zhmc_prometheus_exporter`` command supports the following arguments:

.. code-block:: text

    usage: zhmc_prometheus_exporter [-h] [-c CREDS_FILE] [-m METRICS_FILE]
                                    [-p PORT] [--log-dest DEST] [--log-comp COMP]
                                    [--verbose] [--help-creds] [--help-metrics]

    IBM Z HMC Exporter - a Prometheus exporter for metrics from the IBM Z HMC

    optional arguments:

      -h, --help       show this help message and exit

      -c CREDS_FILE    path name of HMC credentials file. Use --help-creds for
                       details. Default: /etc/zhmc-prometheus-exporter/hmccreds.yaml

      -m METRICS_FILE  path name of metric definition file. Use --help-metrics for
                       details. Default: /etc/zhmc-prometheus-exporter/metrics.yaml

      -p PORT          port for exporting. Default: 9291

      --log-dest DEST  enable logging and set the log destination to one of:
                       stderr,none,FILE. Default: none

      --log-comp COMP  set the components to log to one of: hmc. May be specified
                       multiple times. Default: hmc

      --verbose, -v    increase the verbosity level (max: 2)

      --help-creds     show help for HMC credentials file and exit

      --help-metrics   show help for metric definition file and exit


Exported metric concepts
------------------------

The exporter provides its metrics in the `Prometheus text-based format`_.

All metrics are of the `metric type gauge`_ and follow the
`Prometheus metric naming`_. The names of the metrics are defined in the
:ref:`metric definition file`. The metric names could be changed by users, but
unless there is a strong reason for doing that, it is not recommended.
It is recommended to use the :ref:`sample metric definition file` unchanged.
The metrics mapping in the :ref:`sample metric definition file` is referred to
as the *standard metric definition* in this documentation.

In the standard metric definition, the metric names are structured as follows:

.. code-block:: text

    zhmc_{resource-type}_{metric}_{unit}

Where:

* ``{resource-type}`` is a short lower case term for the type of resource
  the metric applies to, for example ``cpc`` or ``partition``.

* ``{metric}`` is a unique name of the metric within the resource type,
  for example ``processor``.

* ``{unit}`` is the (simple or complex) unit of measurement of the metric
  value. For example, a usage percentage will usually have a unit of
  ``usage_ratio``, while a temperature would have a unit of ``celsius``.

Each metric value applies to a particular instance of a resource. In a
particular set of exported metrics, there are usually metrics for multiple
resource instances. For example, the HMC can manage multiple CPCs, a CPC can
have multiple partitions, and so on. In the exported metrics, the resource
instance is identified using one or more `Prometheus labels`_. Where possible,
the labels identify the resource instances in a hierarchical way from the CPC on
down to the resource to which the metric value applies. For example, a metric
for a partition will have labels ``cpc`` and ``partition`` whose values are the
names of CPC and partition, respectively.

Example for the representation of metric values that are the IFL processor
usage percentages of two partitions in a single CPC:

.. code-block:: text

    # HELP zhmc_partition_ifl_processor_usage_ratio Usage ratio across all IFL processors of the partition
    # TYPE zhmc_partition_ifl_processor_usage_ratio gauge
    zhmc_partition_ifl_processor_usage_ratio{cpc='CPCA',partition='PART1'} 0.42
    zhmc_partition_ifl_processor_usage_ratio{cpc='CPCA',partition='PART2'} 0.07

.. _Prometheus text-based format: https://prometheus.io/docs/instrumenting/exposition_formats/#text-based-format
.. _metric type gauge: https://prometheus.io/docs/concepts/metric_types/#gauge
.. _Prometheus metric naming: https://prometheus.io/docs/practices/naming/
.. _Prometheus labels: https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels

Available metrics
-----------------

The exporter code is agnostic to the actual set of metrics supported by the
HMC. A new metric can immediately be supported by just adding it to the
:ref:`metric definition file`.

The :ref:`sample metric definition file` in the Git repository states in its
header up to which HMC version or Z machine generation the metrics are defined.

The following table shows the mapping between HMC metric groups and exported
Prometheus metrics in the standard metric definition. Note that ensemble and
zBX related metrics are not covered in the standard metric definition (support
for them has been removed in z15). For more details on the HMC metrics, see
section "Metric Groups" in the :term:`HMC API` book.

====================================  ====  ===========================  ======================
HMC Metric Group                      Mode  Prometheus Metrics           Prometheus Labels
====================================  ====  ===========================  ======================
cpc-usage-overview                    C     zhmc_cpc_*                   cpc
logical-partition-usage               C     zhmc_partition_*             cpc, partition
channel-usage                         C     zhmc_channel_*               cpc, channel_css_chpid
crypto-usage                          C     zhmc_crypto_adapter_*        cpc, adapter_pchid
flash-memory-usage                    C     zhmc_flash_memory_adapter_*  cpc, adapter_pchid
roce-usage                            C     zhmc_roce_adapter_*          cpc, adapter_pchid
dpm-system-usage-overview             D     zhmc_cpc_*                   cpc
partition-usage                       D     zhmc_partition_*             cpc, partition
adapter-usage                         D     zhmc_adapter_*               cpc, adapter
network-physical-adapter-port         D     zhmc_port_*                  cpc, adapter, port
partition-attached-network-interface  D     zhmc_nic_*                   cpc, partition, nic
zcpc-environmentals-and-power         C+D   zhmc_cpc_*                   cpc
environmental-power-status            C+D   zhmc_cpc_*                   cpc
zcpc-processor-usage                  C+D   zhmc_processor_*             cpc, processor, type
====================================  ====  ===========================  ======================

Legend:

* Mode: The operational mode of the CPC: C=Classic, D=DPM

As you can see, the ``zhmc_cpc_*`` and ``zhmc_partition_*`` metrics are used
for both DPM mode and classic mode. The names of the metrics are equal if and
only if they have the same meaning in both modes.

The following table shows the Prometheus metrics in the standard metric
definition:

===============================================  ====  ==================================================================
Prometheus Metric                                Mode  Description
===============================================  ====  ==================================================================
zhmc_cpc_processor_usage_ratio                   C+D   Usage ratio across all processors of the CPC
zhmc_cpc_shared_processor_usage_ratio            C+D   Usage ratio across all shared processors of the CPC
zhmc_cpc_dedicated_processor_usage_ratio         C     Usage ratio across all dedicated processors of the CPC
zhmc_cpc_cp_processor_usage_ratio                C+D   Usage ratio across all CP processors of the CPC
zhmc_cpc_cp_shared_processor_usage_ratio         C+D   Usage ratio across all shared CP processors of the CPC
zhmc_cpc_cp_dedicated_processor_usage_ratio      C     Usage ratio across all dedicated CP processors of the CPC
zhmc_cpc_ifl_processor_usage_ratio               C+D   Usage ratio across all IFL processors of the CPC
zhmc_cpc_ifl_shared_processor_usage_ratio        C+D   Usage ratio across all shared IFL processors of the CPC
zhmc_cpc_ifl_dedicated_processor_usage_ratio     C     Usage ratio across all dedicated IFL processors of the CPC
zhmc_cpc_aap_shared_processor_usage_ratio        C     Usage ratio across all shared zAAP processors of the CPC
zhmc_cpc_aap_dedicated_processor_usage_ratio     C     Usage ratio across all dedicated zAAP processors of the CPC
zhmc_cpc_cbp_processor_usage_ratio               C     Usage ratio across all CBP processors of the CPC
zhmc_cpc_cbp_shared_processor_usage_ratio        C     Usage ratio across all shared CBP processors of the CPC
zhmc_cpc_cbp_dedicated_processor_usage_ratio     C     Usage ratio across all dedicated CBP processors of the CPC
zhmc_cpc_icf_processor_usage_ratio               C     Usage ratio across all ICF processors of the CPC
zhmc_cpc_icf_shared_processor_usage_ratio        C     Usage ratio across all shared ICF processors of the CPC
zhmc_cpc_icf_dedicated_processor_usage_ratio     C     Usage ratio across all dedicated ICF processors of the CPC
zhmc_cpc_iip_processor_usage_ratio               C     Usage ratio across all zIIP processors of the CPC
zhmc_cpc_iip_shared_processor_usage_ratio        C     Usage ratio across all shared zIIP processors of the CPC
zhmc_cpc_iip_dedicated_processor_usage_ratio     C     Usage ratio across all dedicated zIIP processors of the CPC
zhmc_cpc_channel_usage_ratio                     C     Usage ratio across all channels of the CPC
zhmc_cpc_accelerator_adapter_usage_ratio         D     Usage ratio across all accelerator adapters of the CPC
zhmc_cpc_crypto_adapter_usage_ratio              D     Usage ratio across all crypto adapters of the CPC
zhmc_cpc_network_adapter_usage_ratio             D     Usage ratio across all network adapters of the CPC
zhmc_cpc_storage_adapter_usage_ratio             D     Usage ratio across all storage adapters of the CPC
zhmc_cpc_power_watts                             C+D   Power consumption of the CPC
zhmc_cpc_ambient_temperature_celsius             C+D   Ambient temperature of the CPC
zhmc_crypto_adapter_usage_ratio                  C     Usage ratio of the crypto adapter
zhmc_flash_memory_adapter_usage_ratio            C     Usage ratio of the flash memory adapter
zhmc_adapter_usage_ratio                         D     Usage ratio of the adapter
zhmc_channel_usage_ratio                         C     Usage ratio of the channel
zhmc_roce_adapter_usage_ratio                    C     Usage ratio of the RoCE adapter
zhmc_partition_processor_usage_ratio             C+D   Usage ratio across all processors of the partition
zhmc_partition_cp_processor_usage_ratio          C     Usage ratio across all CP processors of the partition
zhmc_partition_ifl_processor_usage_ratio         C     Usage ratio across all IFL processors of the partition
zhmc_partition_icf_processor_usage_ratio         C     Usage ratio across all ICF processors of the partition
zhmc_partition_cbp_processor_usage_ratio         C     Usage ratio across all CBP processors of the partition
zhmc_partition_iip_processor_usage_ratio         C     Usage ratio across all IIP processors of the partition
zhmc_partition_accelerator_adapter_usage_ratio   D     Usage ratio of all accelerator adapters of the partition
zhmc_partition_crypto_adapter_usage_ratio        D     Usage ratio of all crypto adapters of the partition
zhmc_partition_network_adapter_usage_ratio       D     Usage ratio of all network adapters of the partition
zhmc_partition_storage_adapter_usage_ratio       D     Usage ratio of all storage adapters of the partition
zhmc_partition_zvm_paging_rate_pages_per_second  C     z/VM paging rate in pages/sec
zhmc_port_bytes_sent_count                       D     Number of Bytes in unicast packets that were sent
zhmc_port_bytes_received_count                   D     Number of Bytes in unicast packets that were received
zhmc_port_packets_sent_count                     D     Number of unicast packets that were sent
zhmc_port_packets_received_count                 D     Number of unicast packets that were received
zhmc_port_packets_sent_dropped_count             D     Number of sent packets that were dropped (resource shortage)
zhmc_port_packets_received_dropped_count         D     Number of received packets that were dropped (resource shortage)
zhmc_port_packets_sent_discarded_count           D     Number of sent packets that were discarded (malformed)
zhmc_port_packets_received_discarded_count       D     Number of received packets that were discarded (malformed)
zhmc_port_multicast_packets_sent_count           D     Number of multicast packets sent
zhmc_port_multicast_packets_received_count       D     Number of multicast packets received
zhmc_port_broadcast_packets_sent_count           D     Number of broadcast packets sent
zhmc_port_broadcast_packets_received_count       D     Number of broadcast packets received
zhmc_port_data_sent_bytes                        D     Amount of data sent over the collection interval
zhmc_port_data_received_bytes                    D     Amount of data received over the collection interval
zhmc_port_data_rate_sent_bytes_per_second        D     Data rate sent over the collection interval
zhmc_port_data_rate_received_bytes_per_second    D     Data rate received over the collection interval
zhmc_port_bandwidth_usage_ratio                  D     Bandwidth usage ratio of the port
zhmc_nic_bytes_sent_count                        D     Number of Bytes in unicast packets that were sent
zhmc_nic_bytes_received_count                    D     Number of Bytes in unicast packets that were received
zhmc_nic_packets_sent_count                      D     Number of unicast packets that were sent
zhmc_nic_packets_received_count                  D     Number of unicast packets that were received
zhmc_nic_packets_sent_dropped_count              D     Number of sent packets that were dropped (resource shortage)
zhmc_nic_packets_received_dropped_count          D     Number of received packets that were dropped (resource shortage)
zhmc_nic_packets_sent_discarded_count            D     Number of sent packets that were discarded (malformed)
zhmc_nic_packets_received_discarded_count        D     Number of received packets that were discarded (malformed)
zhmc_nic_multicast_packets_sent_count            D     Number of multicast packets sent
zhmc_nic_multicast_packets_received_count        D     Number of multicast packets received
zhmc_nic_broadcast_packets_sent_count            D     Number of broadcast packets sent
zhmc_nic_broadcast_packets_received_count        D     Number of broadcast packets received
zhmc_nic_data_sent_bytes                         D     Amount of data sent over the collection interval
zhmc_nic_data_received_bytes                     D     Amount of data received over the collection interval
zhmc_nic_data_rate_sent_bytes_per_second         D     Data rate sent over the collection interval
zhmc_nic_data_rate_received_bytes_per_second     D     Data rate received over the collection interval
zhmc_cpc_humidity_percent                        C+D   Relative humidity
zhmc_cpc_dew_point_celsius                       C+D   Dew point
zhmc_cpc_heat_load_total_btu_per_hour            C+D   Total heat load of the CPC
zhmc_cpc_heat_load_forced_air_btu_per_hour       C+D   Heat load of the CPC covered by forced-air
zhmc_cpc_heat_load_water_btu_per_hour            C+D   Heat load of the CPC covered by water
zhmc_cpc_exhaust_temperature_celsius             C+D   Exhaust temperature of the CPC
zhmc_cpc_power_cord1_phase_a_watts               C+D   Power in Phase A of line cord 1 - 0 if not available
zhmc_cpc_power_cord1_phase_b_watts               C+D   Power in Phase B of line cord 1 - 0 if not available
zhmc_cpc_power_cord1_phase_c_watts               C+D   Power in Phase C of line cord 1 - 0 if not available
zhmc_cpc_power_cord2_phase_a_watts               C+D   Power in Phase A of line cord 2 - 0 if not available
zhmc_cpc_power_cord2_phase_b_watts               C+D   Power in Phase B of line cord 2 - 0 if not available
zhmc_cpc_power_cord2_phase_c_watts               C+D   Power in Phase C of line cord 2 - 0 if not available
zhmc_cpc_power_cord3_phase_a_watts               C+D   Power in Phase A of line cord 3 - 0 if not available
zhmc_cpc_power_cord3_phase_b_watts               C+D   Power in Phase B of line cord 3 - 0 if not available
zhmc_cpc_power_cord3_phase_c_watts               C+D   Power in Phase C of line cord 3 - 0 if not available
zhmc_cpc_power_cord4_phase_a_watts               C+D   Power in Phase A of line cord 4 - 0 if not available
zhmc_cpc_power_cord4_phase_b_watts               C+D   Power in Phase B of line cord 4 - 0 if not available
zhmc_cpc_power_cord4_phase_c_watts               C+D   Power in Phase C of line cord 4 - 0 if not available
zhmc_cpc_power_cord5_phase_a_watts               C+D   Power in Phase A of line cord 5 - 0 if not available
zhmc_cpc_power_cord5_phase_b_watts               C+D   Power in Phase B of line cord 5 - 0 if not available
zhmc_cpc_power_cord5_phase_c_watts               C+D   Power in Phase C of line cord 5 - 0 if not available
zhmc_cpc_power_cord6_phase_a_watts               C+D   Power in Phase A of line cord 6 - 0 if not available
zhmc_cpc_power_cord6_phase_b_watts               C+D   Power in Phase B of line cord 6 - 0 if not available
zhmc_cpc_power_cord6_phase_c_watts               C+D   Power in Phase C of line cord 6 - 0 if not available
zhmc_cpc_power_cord7_phase_a_watts               C+D   Power in Phase A of line cord 7 - 0 if not available
zhmc_cpc_power_cord7_phase_b_watts               C+D   Power in Phase B of line cord 7 - 0 if not available
zhmc_cpc_power_cord7_phase_c_watts               C+D   Power in Phase C of line cord 7 - 0 if not available
zhmc_cpc_power_cord8_phase_a_watts               C+D   Power in Phase A of line cord 8 - 0 if not available
zhmc_cpc_power_cord8_phase_b_watts               C+D   Power in Phase B of line cord 8 - 0 if not available
zhmc_cpc_power_cord8_phase_c_watts               C+D   Power in Phase C of line cord 8 - 0 if not available
zhmc_processor_usage_ratio                       C+D   Usage ratio of the processor
zhmc_processor_smt_mode_percent                  C+D   Percentage of time the processor was in in SMT mode
zhmc_processor_smt_thread0_usage_ratio           C+D   Usage ratio of thread 0 of the processor when in SMT mode
zhmc_processor_smt_thread1_usage_ratio           C+D   Usage ratio of thread 1 of the processor when in SMT mode
===============================================  ====  ==================================================================

HMC credentials file
--------------------

The *HMC credentials file* tells the exporter which HMC to talk to for
obtaining metrics, and which userid and password to use for logging on to
the HMC.

In addition, it allows specifying additional labels to be used in all
metrics exported to Prometheus. This can be used for defining labels that
identify the environment managed by the HMC, in cases where metrics from
multiple instances of exporters and HMCs come together.

The HMC credentials file is in YAML format and has the following structure:

.. code-block:: yaml

    metrics:
      hmc: {hmc-ip-address}
      userid: {hmc-userid}
      password: {hmc-password}

    extra_labels:  # optional
      # list of labels:
      - name: {label-name}
        value: {label-value}

Where:

* ``{hmc-ip-address}`` is the IP address of the HMC.

* ``{hmc-userid}`` is the userid on the HMC to be used for logging on.

* ``{hmc-password}`` is the password of that userid.

* ``{label-name}`` is the label name.

* ``{label-value}`` is the label value. The string value is used directly
  without any further interpretation.

Sample HMC credentials file
---------------------------

The following is a sample HMC credentials file (``hmccreds.yaml``).

The file can be downloaded from the Git repo as
`examples/hmccreds.yaml <https://github.com/zhmcclient/zhmc-prometheus-exporter/blob/master/examples/hmccreds.yaml>`_.

.. literalinclude:: ../examples/hmccreds.yaml
  :language: yaml

Metric definition file
----------------------

The *metric definition file* maps the metrics returned by the HMC to metrics
exported to Prometheus.

Furthermore, the metric definition file allows optimizing the access time to
the HMC by disabling the fetching of metrics that are not needed.

The metric definition file is in YAML format and has the following structure:

.. code-block:: yaml

    metric_groups:
      # dictionary of metric groups:
      {hmc-metric-group}:
        prefix: {resource-type}
        fetch: {fetch-bool}
        if: {fetch-condition}  # optional
        labels:
          # list of labels:
          - name: {label-name}
            value: {label-value}

    metrics:
      # dictionary of metric groups and metrics
      {hmc-metric-group}:
        {hmc-metric}:
          percent: {percent-bool}
          exporter_name: {metric}_{unit}
          exporter_desc: {help}

Where:

* ``{hmc-metric-group}`` is the name of the metric group on the HMC.

* ``{hmc-metric}`` is the name of the metric (within the metric group) on the
  HMC.

* ``{resource-type}`` is a short lower case term for the type of resource
  the metric applies to, for example ``cpc`` or ``partition``. It is used
  in the Prometheus metric name directly after the initial ``zhmc_``.

* ``{fetch-bool}`` is a boolean indicating whether the user wants this metric
  group to be fetched from the HMC. For the metric group to actually be fetched,
  the ``if`` property, if specified, also needs to evaluate to True.

* ``{fetch-condition}`` is a string that is evaluated as a Python expression and
  that indicates whether the metric group can be fetched. For the metric group
  to actually be fetched, the ``fetch`` property also needs to be True.
  The expression may contain the ``hmc_version`` variable which evaluates to
  the HMC version. The HMC versions are evaluated as tuples of integers,
  padding them to 3 version parts by appending 0 if needed.

* ``{label-name}`` is the label name.

* ``{label-value}`` identifies where the label value is taken from, as follows:

  - ``resource`` the name of the resource reported by the HMC for the metric.
    This is the normal case and also the default.

  - ``resource.parent`` the name of the parent resource of the resource
    reported by the HMC for the metric. This is useful for resources that
    are inside of the CPC, such as adapters or partitions, to get back to the
    CPC containing them.

  - ``resource.parent.parent`` the name of the grand parent resource of the
    resource reported by the HMC for the metric. This is useful for resources
    that are inside of the CPC at the second level, such as NICs or adapter
    ports, to get back to the CPC containing them.

  - ``{hmc-metric-name}`` the name of the HMC metric within the same metric
    group whose metric value should be used as a label value. This can be used
    to use accompanying HMC metrics that are actually identifiers for resources,
    a labels for the actual metric. Example: The HMC returns metrics group
    ``channel-usage`` with metric ``channel-usage`` that has the actual value
    and metric ``channel-name`` that identifies the channel to which the metric
    value belongs. The following fragment utilizes the ``channel-name`` metric
    as a label for the ``channel-usage`` metric:

    .. code-block:: yaml

        metric_groups:
          channel-usage:
            prefix: channel
            fetch: True
            labels:
              - name: cpc
                value: resource
              - name: channel_css_chpid
                value: channel-name
        metrics:
          channel-usage:
            channel-usage:
              percent: True
              exporter_name: usage_ratio
              exporter_desc: Usage ratio of the channel

* ``{percent-bool}`` is a boolean indicating whether the metric value should
  be divided by 100. The reason for this is that the HMC metrics represent
  percentages such that a value of 100 means 100% = 1, while Prometheus
  represents them such that a value of 1.0 means 100% = 1.

* ``{metric}_{unit}`` is the Prometheus local metric name and unit in
  the full metric name ``zhmc_{resource-type}_{metric}_{unit}``.

* ``{help}`` is the description text that is exported as ``# HELP``.

Sample metric definition file
-----------------------------

The following is a sample metric definition file (``metrics.yaml``) that defines
all metrics as of HMC 2.15 (z15).

The file can be downloaded from the Git repo as
`examples/metrics.yaml <https://github.com/zhmcclient/zhmc-prometheus-exporter/blob/master/examples/metrics.yaml>`_.

.. literalinclude:: ../examples/metrics.yaml
  :language: yaml

Sample output to Prometheus
---------------------------

The following is sample output of the exporter to Prometheus. It is from a z14
system in DPM mode and was created with an extra label ``pod=wdc04-05``, and
with all metric groups enabled. The data has been reduced to show only three
example partitions (but all adapters and processors):

.. literalinclude:: ../examples/prometheus.out
  :language: text

Demo setup with Grafana
-----------------------

This section describes a demo setup with a Prometheus server and with the Grafana
frontend for visualizing the metrics.

The Prometheus server scrapes the metrics from the exporter. The Grafana server
provides a HTML based web server that visualises the metrics in a dashboard.

The following diagram shows the demo setup:

.. image:: deployment.png
    :align: center
    :alt: Demo setup

Perform these steps for setting it up:

* Download and install Prometheus from the `Prometheus download page`_ or
  using your OS-specific package manager.

  Copy the sample Prometheus configuration file (``examples/prometheus.yaml`` in
  the Git repo) as ``prometheus.yaml`` into some directory where you will run
  the Prometheus server. The host:port for contacting the exporter is already
  set to ``localhost:9291`` and it can be changed as needed.

  Run the Prometheus server as follows:

  .. code-block:: bash

      $ prometheus --config.file=prometheus.yaml

  For details, see the `Prometheus guide`_.

.. _Prometheus download page: https://prometheus.io/download/
.. _Prometheus guide: https://prometheus.io/docs/prometheus/latest/getting_started/

* Download and install Grafana from the `Grafana download page`_ or
  using your OS-specific package manager.

  Run the Grafana server as follows:

  .. code-block:: bash

      $ grafana-server -homepath {homepath} web

  Where:

  * ``{homepath}`` is the path name of the directory with the ``conf`` and
    ``data`` directories, for example
    ``/usr/local/Cellar/grafana/7.3.4/share/grafana`` on macOS when Grafana
    was installed using Homebrew.

  By default, the web interface will be on ``localhost:3000``. This can be
  changed as needed. For details, see the `Prometheus guide on Grafana`_.

.. _Grafana download page: https://grafana.com/grafana/download
.. _Prometheus guide on Grafana: https://prometheus.io/docs/visualization/grafana/

* Direct your web browser at https://localhost:3000 and log on using admin/admin.

  Create a data source in Grafana with:

  * Name: ``ZHMC_Prometheus``
  * URL: http://localhost:9090

  Create a dashboard in Grafana by importing the sample dashboard
  (``examples/grafana.json`` in the Git repo). It will use the data source
  ``ZHMC_Prometheus``.


Logging
-------

The exporter supports logging the interactions with the HMC to stderr or to
a file. Logging is enabled by using the ``--log-dest DEST`` option where
``DEST`` can be the keyword ``stderr`` or the path name of a log file.

Examples:

.. code-block:: bash

    $ zhmc_prometheus_exporter --log-dest stderr ...
    $ zhmc_prometheus_exporter --log-dest mylog.log ...

At this point, only the HMC interactions can be logged, so the only valid value
for the ``--log-comp`` option is ``hmc``. That is also the default component
that is logged (when enabled via ``--log-dest``).
