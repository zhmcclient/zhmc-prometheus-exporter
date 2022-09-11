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

.. When updating the command help, use a 100 char wide terminal
.. code-block:: text

    usage: zhmc_prometheus_exporter [-h] [-c CREDS_FILE] [-m METRICS_FILE] [-p PORT] [--log DEST]
                                    [--log-comp COMP[=LEVEL]] [--verbose] [--help-creds]
                                    [--help-metrics]

    IBM Z HMC Exporter - a Prometheus exporter for metrics from the IBM Z HMC

    optional arguments:

      -h, --help            show this help message and exit

      -c CREDS_FILE         path name of HMC credentials file. Use --help-creds for details. Default:
                            /etc/zhmc-prometheus-exporter/hmccreds.yaml

      -m METRICS_FILE       path name of metric definition file. Use --help-metrics for details.
                            Default: /etc/zhmc-prometheus-exporter/metrics.yaml

      -p PORT               port for exporting. Default: 9291

      --log DEST            enable logging and set a log destination (stderr, syslog, FILE). Default:
                            no logging

      --log-comp COMP[=LEVEL]
                            set a logging level (error, warning, info, debug, off, default: warning)
                            for a component (exporter, hmc, jms, all). May be specified multiple
                            times; options add to the default of: all=warning

      --syslog-facility TEXT
                            syslog facility (user, local0, local1, local2, local3, local4, local5,
                            local6, local7) when logging to the system log. Default: user

      --verbose, -v         increase the verbosity level (max: 2)

      --help-creds          show help for HMC credentials file and exit

      --help-metrics        show help for metric definition file and exit


HMC userid requirements
-----------------------

This section describes the requirements on the HMC userid that is used by
the ``zhmc_prometheus_exporter`` command.

To return all metrics supported by the command, the HMC userid must have the
following permissions:

* Object access permission to the objects for which metrics should be returned.

  If the userid does not have object access permission to a particular object,
  the exporter will behave as if the object did not exist, i.e. it will
  successfully return metrics for objects with access permission, and ignore
  any others.

  The exporter can return metrics for the following types of objects. To
  return metrics for all existing objects, the userid must have object access
  permission to all of the following objects:

  - CPCs
  - On CPCs in DPM mode:
    - Adapters
    - Partitions
    - NICs
  - On CPCs in classic mode:
    - LPARs

* Task permission for the "Manage Secure Execution Keys" task.

  This is used by the exporter during the 'Get CPC Properties' operation, but
  it does not utilize the CPC properties returned that way (room for future
  optimization).


HMC certificate
---------------

By default, the HMC is configured with a self-signed certificate. That is the
X.509 certificate presented by the HMC as the server certificate during SSL/TLS
handshake at its Web Services API.

Starting with version 0.7, the 'zhmc_prometheus_exporter' command will reject
self-signed certificates by default.

The HMC should be configured to use a CA-verifiable certificate. This can be
done in the HMC task "Certificate Management". See also the :term:`HMC Security`
book and Chapter 3 "Invoking API operations" in the :term:`HMC API` book.

Starting with version 0.7, the 'zhmc_prometheus_exporter' command provides
control knobs for the verification of the HMC certificate via the
``verify_cert`` attribute in the :ref:`HMC credentials file`, as follows:

* Not specified or specified as ``true`` (default): Verify the HMC certificate
  using the CA certificates from the first of these locations:

  - The certificate file or directory in the ``REQUESTS_CA_BUNDLE`` environment
    variable, if set
  - The certificate file or directory in the ``CURL_CA_BUNDLE`` environment
    variable, if set
  - The `Python 'certifi' package <https://pypi.org/project/certifi/>`_
    (which contains the
    `Mozilla Included CA Certificate List <https://wiki.mozilla.org/CA/Included_Certificates>`_).

* Specified with a string value: An absolute path or a path relative to the
  directory of the HMC credentials file. Verify the HMC certificate using the CA
  certificates in the specified certificate file or directory.

* Specified as ``false``: Do not verify the HMC certificate.
  Not verifying the HMC certificate means that hostname mismatches, expired
  certificates, revoked certificates, or otherwise invalid certificates will not
  be detected. Since this mode makes the connection vulnerable to
  man-in-the-middle attacks, it is insecure and should not be used in production
  environments.

If a certificate file is specified (using any of the ways listed above), that
file must be in PEM format and must contain all CA certificates that are
supposed to be used. Usually they are in the order from leaf to root, but
that is not a hard requirement. The single certificates are concatenated
in the file.

If a certificate directory is specified (using any of the ways listed above),
it must contain PEM files with all CA certificates that are supposed to be used,
and copies of the PEM files or symbolic links to them in the hashed format
created by the OpenSSL command ``c_rehash``.

An X.509 certificate in PEM format is base64-encoded, begins with the line
``-----BEGIN CERTIFICATE-----``, and ends with the line
``-----END CERTIFICATE-----``.
More information about the PEM format is for example on this
`www.ssl.com page <https://www.ssl.com/guide/pem-der-crt-and-cer-x-509-encodings-and-conversions>`_
or in this `serverfault.com answer <https://serverfault.com/a/9717/330351>`_.

Note that setting the ``REQUESTS_CA_BUNDLE`` or ``CURL_CA_BUNDLE`` environment
variables influences other programs that use these variables, too.

For more information, see the
`Security <https://python-zhmcclient.readthedocs.io/en/latest/security.html>`_
section in the documentation of the 'zhmcclient' package.


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

The exporter supports two types of metrics. These metrics are differently
retrieved from the HMC, but they are exported to Prometheus in the same way:

* HMC metric service based - These metrics are retrieved from the HMC using the
  "Get Metric Context" operation each time Prometheus retrieves metrics from the
  exporter.

* HMC resource property based - These metrics are actually the values of
  properties of HMC resources, such as the number of processors assigned
  to a partition. The exporter maintains representations of the corresponding
  resources in memory. These representations are automatically and
  asynchronously updated via HMC object notifications. When Prometheus retrieves
  these metrics from the exporter, the exporter always has up-to-date resource
  representations and can immediately return them without having to turn around
  for getting them from the HMC.

  Resources that no longer exist on the HMC are automatically not exported
  anymore. Resources that were created on the HMC since the exporter was
  started are not detected.

The exporter code is agnostic to the actual set of metrics supported by the HMC.
A new metric exposed by the HMC metric service or a new property added to one of
the auto-updated resources can immediately be supported by just adding it to
the :ref:`metric definition file`.

The :ref:`sample metric definition file` in the Git repository states in its
header up to which HMC version or Z machine generation the metrics are defined.

The following table shows the mapping between exporter metric groups and
exported Prometheus metrics in the standard metric definition. Note that
ensemble and zBX related metrics are not covered in the standard metric
definition (support for them has been removed in z15). For more details on the
HMC metrics, see section "Metric Groups" in the :term:`HMC API` book.
For more details on the resource properties of CPC and Partition (DPM mode)
and Logical Partition (classic mode), see the corresponding data models
in the :term:`HMC API` book.

====================================  ====  ====  ===========================  ======================
Exporter Metric Group                 Type  Mode  Prometheus Metrics           Prometheus Labels
====================================  ====  ====  ===========================  ======================
cpc-usage-overview                    M     C     zhmc_cpc_*                   cpc
logical-partition-usage               M     C     zhmc_partition_*             cpc, partition
channel-usage                         M     C     zhmc_channel_*               cpc, channel_css_chpid
crypto-usage                          M     C     zhmc_crypto_adapter_*        cpc, adapter_pchid
flash-memory-usage                    M     C     zhmc_flash_memory_adapter_*  cpc, adapter_pchid
roce-usage                            M     C     zhmc_roce_adapter_*          cpc, adapter_pchid
dpm-system-usage-overview             M     D     zhmc_cpc_*                   cpc
partition-usage                       M     D     zhmc_partition_*             cpc, partition
adapter-usage                         M     D     zhmc_adapter_*               cpc, adapter
network-physical-adapter-port         M     D     zhmc_port_*                  cpc, adapter, port
partition-attached-network-interface  M     D     zhmc_nic_*                   cpc, partition, nic
zcpc-environmentals-and-power         M     C+D   zhmc_cpc_*                   cpc
environmental-power-status            M     C+D   zhmc_cpc_*                   cpc
zcpc-processor-usage                  M     C+D   zhmc_processor_*             cpc, processor, type
cpc-resource                          R     C+D   zhmc_cpc_*                   cpc
partition-resource                    R     D     zhmc_partition_*             cpc, partition
logical-partition-resource            R     C     zhmc_partition_*             cpc, partition
====================================  ====  ====  ===========================  ======================

Legend:

* Type:: The type of the metric group: M=metric service, R=resource property
* Mode: The operational mode of the CPC: C=Classic, D=DPM

As you can see, the ``zhmc_cpc_*`` and ``zhmc_partition_*`` metrics are used
for both DPM mode and classic mode. The names of the metrics are equal if and
only if they have the same meaning in both modes.

The following table shows the Prometheus metrics in the standard metric
definition. This includes both metric service and resource property based metrics:

======================================================  ====  ====  ==================================================================
Prometheus Metric                                       Mode  Type  Description
======================================================  ====  ====  ==================================================================
zhmc_cpc_cp_processor_count                             C+D   G     Number of active CP processors
zhmc_cpc_ifl_processor_count                            C+D   G     Number of active IFL processors
zhmc_cpc_icf_processor_count                            C+D   G     Number of active ICF processors
zhmc_cpc_iip_processor_count                            C+D   G     Number of active zIIP processors
zhmc_cpc_aap_processor_count                            C+D   G     Number of active zAAP processors
zhmc_cpc_cbp_processor_count                            C+D   G     Number of active CBP processors
zhmc_cpc_sap_processor_count                            C+D   G     Number of active SAP processors
zhmc_cpc_defective_processor_count                      C+D   G     Number of defective processors of all processor types
zhmc_cpc_spare_processor_count                          C+D   G     Number of spare processors of all processor types
zhmc_cpc_total_memory_mib                               C+D   G     Total amount of installed memory, in MiB
zhmc_cpc_hsa_memory_mib                                 C+D   G     Memory reserved for the base hardware system area (HSA), in MiB
zhmc_cpc_partition_memory_mib                           C+D   G     Memory for use by partitions, in MiB
zhmc_cpc_partition_central_memory_mib                   C+D   G     Memory allocated as central storage across the active partitions, in MiB
zhmc_cpc_partition_expanded_memory_mib                  C+D   G     Memory allocated as expanded storage across the active partitions, in MiB
zhmc_cpc_available_memory_mib                           C+D   G     Memory not allocated to active partitions, in MiB
zhmc_cpc_vfm_increment_gib                              C+D   G     Increment size of VFM, in GiB
zhmc_cpc_total_vfm_gib                                  C+D   G     Total amount of installed VFM, in GiB
zhmc_cpc_processor_usage_ratio                          C+D   G     Usage ratio across all processors of the CPC
zhmc_cpc_shared_processor_usage_ratio                   C+D   G     Usage ratio across all shared processors of the CPC
zhmc_cpc_dedicated_processor_usage_ratio                C     G     Usage ratio across all dedicated processors of the CPC
zhmc_cpc_cp_processor_usage_ratio                       C+D   G     Usage ratio across all CP processors of the CPC
zhmc_cpc_cp_shared_processor_usage_ratio                C+D   G     Usage ratio across all shared CP processors of the CPC
zhmc_cpc_cp_dedicated_processor_usage_ratio             C     G     Usage ratio across all dedicated CP processors of the CPC
zhmc_cpc_ifl_processor_usage_ratio                      C+D   G     Usage ratio across all IFL processors of the CPC
zhmc_cpc_ifl_shared_processor_usage_ratio               C+D   G     Usage ratio across all shared IFL processors of the CPC
zhmc_cpc_ifl_dedicated_processor_usage_ratio            C     G     Usage ratio across all dedicated IFL processors of the CPC
zhmc_cpc_aap_shared_processor_usage_ratio               C     G     Usage ratio across all shared zAAP processors of the CPC
zhmc_cpc_aap_dedicated_processor_usage_ratio            C     G     Usage ratio across all dedicated zAAP processors of the CPC
zhmc_cpc_cbp_processor_usage_ratio                      C     G     Usage ratio across all CBP processors of the CPC
zhmc_cpc_cbp_shared_processor_usage_ratio               C     G     Usage ratio across all shared CBP processors of the CPC
zhmc_cpc_cbp_dedicated_processor_usage_ratio            C     G     Usage ratio across all dedicated CBP processors of the CPC
zhmc_cpc_icf_processor_usage_ratio                      C     G     Usage ratio across all ICF processors of the CPC
zhmc_cpc_icf_shared_processor_usage_ratio               C     G     Usage ratio across all shared ICF processors of the CPC
zhmc_cpc_icf_dedicated_processor_usage_ratio            C     G     Usage ratio across all dedicated ICF processors of the CPC
zhmc_cpc_iip_processor_usage_ratio                      C     G     Usage ratio across all zIIP processors of the CPC
zhmc_cpc_iip_shared_processor_usage_ratio               C     G     Usage ratio across all shared zIIP processors of the CPC
zhmc_cpc_iip_dedicated_processor_usage_ratio            C     G     Usage ratio across all dedicated zIIP processors of the CPC
zhmc_cpc_channel_usage_ratio                            C     G     Usage ratio across all channels of the CPC
zhmc_cpc_accelerator_adapter_usage_ratio                D     G     Usage ratio across all accelerator adapters of the CPC
zhmc_cpc_crypto_adapter_usage_ratio                     D     G     Usage ratio across all crypto adapters of the CPC
zhmc_cpc_network_adapter_usage_ratio                    D     G     Usage ratio across all network adapters of the CPC
zhmc_cpc_storage_adapter_usage_ratio                    D     G     Usage ratio across all storage adapters of the CPC
zhmc_cpc_power_watts                                    C+D   G     Power consumption of the CPC
zhmc_cpc_ambient_temperature_celsius                    C+D   G     Ambient temperature of the CPC
zhmc_cpc_humidity_percent                               C+D   G     Relative humidity
zhmc_cpc_dew_point_celsius                              C+D   G     Dew point
zhmc_cpc_heat_load_total_btu_per_hour                   C+D   G     Total heat load of the CPC
zhmc_cpc_heat_load_forced_air_btu_per_hour              C+D   G     Heat load of the CPC covered by forced-air
zhmc_cpc_heat_load_water_btu_per_hour                   C+D   G     Heat load of the CPC covered by water
zhmc_cpc_exhaust_temperature_celsius                    C+D   G     Exhaust temperature of the CPC
zhmc_cpc_power_cord1_phase_a_watts                      C+D   G     Power in Phase A of line cord 1 - 0 if not available
zhmc_cpc_power_cord1_phase_b_watts                      C+D   G     Power in Phase B of line cord 1 - 0 if not available
zhmc_cpc_power_cord1_phase_c_watts                      C+D   G     Power in Phase C of line cord 1 - 0 if not available
zhmc_cpc_power_cord2_phase_a_watts                      C+D   G     Power in Phase A of line cord 2 - 0 if not available
zhmc_cpc_power_cord2_phase_b_watts                      C+D   G     Power in Phase B of line cord 2 - 0 if not available
zhmc_cpc_power_cord2_phase_c_watts                      C+D   G     Power in Phase C of line cord 2 - 0 if not available
zhmc_cpc_power_cord3_phase_a_watts                      C+D   G     Power in Phase A of line cord 3 - 0 if not available
zhmc_cpc_power_cord3_phase_b_watts                      C+D   G     Power in Phase B of line cord 3 - 0 if not available
zhmc_cpc_power_cord3_phase_c_watts                      C+D   G     Power in Phase C of line cord 3 - 0 if not available
zhmc_cpc_power_cord4_phase_a_watts                      C+D   G     Power in Phase A of line cord 4 - 0 if not available
zhmc_cpc_power_cord4_phase_b_watts                      C+D   G     Power in Phase B of line cord 4 - 0 if not available
zhmc_cpc_power_cord4_phase_c_watts                      C+D   G     Power in Phase C of line cord 4 - 0 if not available
zhmc_cpc_power_cord5_phase_a_watts                      C+D   G     Power in Phase A of line cord 5 - 0 if not available
zhmc_cpc_power_cord5_phase_b_watts                      C+D   G     Power in Phase B of line cord 5 - 0 if not available
zhmc_cpc_power_cord5_phase_c_watts                      C+D   G     Power in Phase C of line cord 5 - 0 if not available
zhmc_cpc_power_cord6_phase_a_watts                      C+D   G     Power in Phase A of line cord 6 - 0 if not available
zhmc_cpc_power_cord6_phase_b_watts                      C+D   G     Power in Phase B of line cord 6 - 0 if not available
zhmc_cpc_power_cord6_phase_c_watts                      C+D   G     Power in Phase C of line cord 6 - 0 if not available
zhmc_cpc_power_cord7_phase_a_watts                      C+D   G     Power in Phase A of line cord 7 - 0 if not available
zhmc_cpc_power_cord7_phase_b_watts                      C+D   G     Power in Phase B of line cord 7 - 0 if not available
zhmc_cpc_power_cord7_phase_c_watts                      C+D   G     Power in Phase C of line cord 7 - 0 if not available
zhmc_cpc_power_cord8_phase_a_watts                      C+D   G     Power in Phase A of line cord 8 - 0 if not available
zhmc_cpc_power_cord8_phase_b_watts                      C+D   G     Power in Phase B of line cord 8 - 0 if not available
zhmc_cpc_power_cord8_phase_c_watts                      C+D   G     Power in Phase C of line cord 8 - 0 if not available
zhmc_cpc_status_int                                     C+D   G     Status as integer
zhmc_cpc_has_unacceptable_status                        C+D   G     Boolean indicating whether the CPC has an unacceptable status
zhmc_processor_usage_ratio                              C+D   G     Usage ratio of the processor
zhmc_processor_smt_mode_percent                         C+D   G     Percentage of time the processor was in in SMT mode
zhmc_processor_smt_thread0_usage_ratio                  C+D   G     Usage ratio of thread 0 of the processor when in SMT mode
zhmc_processor_smt_thread1_usage_ratio                  C+D   G     Usage ratio of thread 1 of the processor when in SMT mode
zhmc_partition_processor_usage_ratio                    C+D   G     Usage ratio across all processors of the partition
zhmc_partition_cp_processor_usage_ratio                 C     G     Usage ratio across all CP processors of the partition
zhmc_partition_ifl_processor_usage_ratio                C     G     Usage ratio across all IFL processors of the partition
zhmc_partition_icf_processor_usage_ratio                C     G     Usage ratio across all ICF processors of the partition
zhmc_partition_cbp_processor_usage_ratio                C     G     Usage ratio across all CBP processors of the partition
zhmc_partition_iip_processor_usage_ratio                C     G     Usage ratio across all IIP processors of the partition
zhmc_partition_accelerator_adapter_usage_ratio          D     G     Usage ratio of all accelerator adapters of the partition
zhmc_partition_crypto_adapter_usage_ratio               D     G     Usage ratio of all crypto adapters of the partition
zhmc_partition_network_adapter_usage_ratio              D     G     Usage ratio of all network adapters of the partition
zhmc_partition_storage_adapter_usage_ratio              D     G     Usage ratio of all storage adapters of the partition
zhmc_partition_zvm_paging_rate_pages_per_second         C     G     z/VM paging rate in pages/sec
zhmc_partition_processor_mode_int                       C+D   G     Allocation mode for processors as an integer (0=shared, 1=dedicated)
zhmc_partition_threads_per_processor_ratio              D     G     Number of threads per processor used by OS
zhmc_partition_defined_capacity_msu_per_hour            C     G     Defined capacity expressed in terms of MSU per hour
zhmc_partition_workload_manager_is_enabled              C     G     Boolean indicating whether z/OS WLM is allowed to change processing weight related properties (0=false, 1=true)
zhmc_partition_cp_processor_count                       C+D   G     Number of CP processors allocated to the active partition
zhmc_partition_cp_processor_count_is_capped             C+D   G     Boolean indicating whether absolute capping is enabled for CP processors (0=false, 1=true)
zhmc_partition_cp_processor_count_cap                   C+D   G     Maximum number of CP processors that can be used if absolute capping is enabled, else 0
zhmc_partition_cp_reserved_processor_count              C     G     Number of CP processors reserved for the active partition
zhmc_partition_cp_initial_processing_weight             C+D   G     Initial CP processing weight for the active partition in shared mode
zhmc_partition_cp_minimum_processing_weight             C+D   G     Minimum CP processing weight for the active partition in shared mode
zhmc_partition_cp_maximum_processing_weight             C+D   G     Maximum CP processing weight for the active partition in shared mode
zhmc_partition_cp_current_processing_weight             C+D   G     Current CP processing weight for the active partition in shared mode
zhmc_partition_cp_processor_count_cap                   D     G     Maximum number of CP processors to be used when absolute CP processor capping is enabled
zhmc_partition_cp_initial_processing_weight_is_capped   C+D   G     Boolean indicating whether the initial CP processing weight is capped (0=false, 1=true)
zhmc_partition_cp_current_processing_weight_is_capped   C     G     Boolean indicating whether the current CP processing weight is capped (0=false, 1=true)
zhmc_partition_ifl_processor_count                      C+D   G     Number of IFL processors allocated to the active partition
zhmc_partition_ifl_processor_count_is_capped            C+D   G     Boolean indicating whether absolute capping is enabled for IFL processors (0=false, 1=true)
zhmc_partition_ifl_processor_count_cap                  C+D   G     Maximum number of IFL processors that can be used if absolute capping is enabled, else 0
zhmc_partition_ifl_reserved_processor_count             C     G     Number of IFL processors reserved for the active partition
zhmc_partition_ifl_initial_processing_weight            C+D   G     Initial IFL processing weight for the active partition in shared mode
zhmc_partition_ifl_minimum_processing_weight            C+D   G     Minimum IFL processing weight for the active partition in shared mode
zhmc_partition_ifl_maximum_processing_weight            C+D   G     Maximum IFL processing weight for the active partition in shared mode
zhmc_partition_ifl_current_processing_weight            C+D   G     Current IFL processing weight for the active partition in shared mode
zhmc_partition_ifl_processor_count_cap                  D     G     Maximum number of IFL processors to be used when absolute IFL processor capping is enabled
zhmc_partition_ifl_initial_processing_weight_is_capped  C+D   G     Boolean indicating whether the initial IFL processing weight is capped (0=false, 1=true)
zhmc_partition_ifl_current_processing_weight_is_capped  C     G     Boolean indicating whether the current IFL processing weight is capped (0=false, 1=true)
zhmc_partition_icf_processor_count                      C     G     Number of ICF processors currently allocated to the active partition
zhmc_partition_icf_processor_count_is_capped            C     G     Boolean indicating whether absolute capping is enabled for ICF processors (0=false, 1=true)
zhmc_partition_icf_processor_count_cap                  C     G     Maximum number of ICF processors that can be used if absolute capping is enabled, else 0
zhmc_partition_icf_reserved_processor_count             C     G     Number of ICF processors reserved for the active partition
zhmc_partition_icf_initial_processing_weight            C     G     Initial ICF processing weight for the active partition in shared mode
zhmc_partition_icf_minimum_processing_weight            C     G     Minimum ICF processing weight for the active partition in shared mode
zhmc_partition_icf_maximum_processing_weight            C     G     Maximum ICF processing weight for the active partition in shared mode
zhmc_partition_icf_current_processing_weight            C     G     Current ICF processing weight for the active partition in shared mode
zhmc_partition_icf_initial_processing_weight_is_capped  C     G     Boolean indicating whether the initial ICF processing weight is capped (0=false, 1=true)
zhmc_partition_icf_current_processing_weight_is_capped  C     G     Boolean indicating whether the current ICF processing weight is capped (0=false, 1=true)
zhmc_partition_iip_processor_count                      C     G     Number of zIIP processors currently allocated to the active partition
zhmc_partition_iip_processor_count_is_capped            C     G     Boolean indicating whether absolute capping is enabled for zIIP processors (0=false, 1=true)
zhmc_partition_iip_processor_count_cap                  C     G     Maximum number of zIIP processors that can be used if absolute capping is enabled, else 0
zhmc_partition_iip_reserved_processor_count             C     G     Number of zIIP processors reserved for the active partition
zhmc_partition_iip_initial_processing_weight            C     G     Initial zIIP processing weight for the active partition in shared mode
zhmc_partition_iip_minimum_processing_weight            C     G     Minimum zIIP processing weight for the active partition in shared mode
zhmc_partition_iip_maximum_processing_weight            C     G     Maximum zIIP processing weight for the active partition in shared mode
zhmc_partition_iip_current_processing_weight            C     G     Current zIIP processing weight for the active partition in shared mode
zhmc_partition_iip_initial_processing_weight_is_capped  C     G     Boolean indicating whether the initial zIIP processing weight is capped (0=false, 1=true)
zhmc_partition_iip_current_processing_weight_is_capped  C     G     Boolean indicating whether the current zIIP processing weight is capped (0=false, 1=true)
zhmc_partition_aap_processor_count_is_capped            C     G     Boolean indicating whether absolute capping is enabled for zAAP processors (0=false, 1=true)
zhmc_partition_aap_processor_count_cap                  C     G     Maximum number of zAAP processors that can be used if absolute capping is enabled, else 0
zhmc_partition_aap_initial_processing_weight            C     G     Initial zAAP processing weight for the active partition in shared mode
zhmc_partition_aap_minimum_processing_weight            C     G     Minimum zAAP processing weight for the active partition in shared mode
zhmc_partition_aap_maximum_processing_weight            C     G     Maximum zAAP processing weight for the active partition in shared mode
zhmc_partition_aap_current_processing_weight            C     G     Current zAAP processing weight for the active partition in shared mode
zhmc_partition_aap_initial_processing_weight_is_capped  C     G     Boolean indicating whether the initial zAAP processing weight is capped (0=false, 1=true)
zhmc_partition_aap_current_processing_weight_is_capped  C     G     Boolean indicating whether the current zAAP processing weight is capped (0=false, 1=true)
zhmc_partition_cbp_processor_count_is_capped            C     G     Boolean indicating whether absolute capping is enabled for CBP processors (0=false, 1=true)
zhmc_partition_cbp_processor_count_cap                  C     G     Maximum number of CBP processors that can be used if absolute capping is enabled, else 0
zhmc_partition_cbp_initial_processing_weight            C     G     Initial CBP processing weight for the active partition in shared mode
zhmc_partition_cbp_minimum_processing_weight            C     G     Minimum CBP processing weight for the active partition in shared mode
zhmc_partition_cbp_maximum_processing_weight            C     G     Maximum CBP processing weight for the active partition in shared mode
zhmc_partition_cbp_current_processing_weight            C     G     Current CBP processing weight for the active partition in shared mode
zhmc_partition_cbp_initial_processing_weight_is_capped  C     G     Boolean indicating whether the initial CBP processing weight is capped (0=false, 1=true)
zhmc_partition_cbp_current_processing_weight_is_capped  C     G     Boolean indicating whether the current CBP processing weight is capped (0=false, 1=true)
zhmc_partition_initial_memory_mib                       D     G     Initial amount of memory allocated to the partition when it becomes active, in MiB
zhmc_partition_reserved_memory_mib                      D     G     Amount of reserved memory (maximum memory minus initial memory), in MiB
zhmc_partition_maximum_memory_mib                       D     G     Maximum amount of memory to which the OS can increase, in MiB
zhmc_partition_initial_central_memory_mib               C     G     Amount of central memory initially allocated to the active partition in MiB, else 0
zhmc_partition_current_central_memory_mib               C     G     Amount of central memory currently allocated to the active partition, in MiB, else 0
zhmc_partition_maximum_central_memory_mib               C     G     Maximum amount of central memory to which the operating system running in the active partition can increase, in MiB
zhmc_partition_initial_expanded_memory_mib              C     G     Amount of expanded memory initially allocated to the active partition in MiB, else 0
zhmc_partition_current_expanded_memory_mib              C     G     Amount of expanded memory currently allocated to the active partition, in MiB, else 0
zhmc_partition_maximum_expanded_memory_mib              C     G     Maximum amount of expanded memory to which the operating system running in the active partition can increase, in MiB
zhmc_partition_initial_vfm_memory_gib                   C     G     Initial amount of VFM memory to be allocated at partition activation, in GiB
zhmc_partition_maximum_vfm_memory_gib                   C     G     Maximum amount of VFM memory that can be allocated to the active partition, in GiB
zhmc_partition_current_vfm_memory_gib                   C     G     Current amount of VFM memory that is allocated to the active partition, in GiB
zhmc_partition_status_int                               D     G     Partition status as integer (0=active, 1=degraded, 10=paused, 11=stopped, 12=starting, 13=stopping, 20=reservation-error, 21=terminated, 22=communications-not-active, 23=status-check, 99=unsupported value)
zhmc_partition_lpar_status_int                          C     G     LPAR status as integer (0=operating, 1=not-operating, 2=not-activated, 10=exceptions, 99=unsupported value)
zhmc_partition_has_unacceptable_status                  C+D   G     Boolean indicating whether the partition has an unacceptable status
zhmc_crypto_adapter_usage_ratio                         C     G     Usage ratio of the crypto adapter
zhmc_flash_memory_adapter_usage_ratio                   C     G     Usage ratio of the flash memory adapter
zhmc_adapter_usage_ratio                                D     G     Usage ratio of the adapter
zhmc_channel_usage_ratio                                C     G     Usage ratio of the channel
zhmc_roce_adapter_usage_ratio                           C     G     Usage ratio of the RoCE adapter
zhmc_port_bytes_sent_count                              D     C     Number of Bytes in unicast packets that were sent
zhmc_port_bytes_received_count                          D     C     Number of Bytes in unicast packets that were received
zhmc_port_packets_sent_count                            D     C     Number of unicast packets that were sent
zhmc_port_packets_received_count                        D     C     Number of unicast packets that were received
zhmc_port_packets_sent_dropped_count                    D     C     Number of sent packets that were dropped (resource shortage)
zhmc_port_packets_received_dropped_count                D     C     Number of received packets that were dropped (resource shortage)
zhmc_port_packets_sent_discarded_count                  D     C     Number of sent packets that were discarded (malformed)
zhmc_port_packets_received_discarded_count              D     C     Number of received packets that were discarded (malformed)
zhmc_port_multicast_packets_sent_count                  D     C     Number of multicast packets sent
zhmc_port_multicast_packets_received_count              D     C     Number of multicast packets received
zhmc_port_broadcast_packets_sent_count                  D     C     Number of broadcast packets sent
zhmc_port_broadcast_packets_received_count              D     C     Number of broadcast packets received
zhmc_port_data_sent_bytes                               D     G     Amount of data sent over the collection interval
zhmc_port_data_received_bytes                           D     G     Amount of data received over the collection interval
zhmc_port_data_rate_sent_bytes_per_second               D     G     Data rate sent over the collection interval
zhmc_port_data_rate_received_bytes_per_second           D     G     Data rate received over the collection interval
zhmc_port_bandwidth_usage_ratio                         D     G     Bandwidth usage ratio of the port
zhmc_nic_bytes_sent_count                               D     C     Number of Bytes in unicast packets that were sent
zhmc_nic_bytes_received_count                           D     C     Number of Bytes in unicast packets that were received
zhmc_nic_packets_sent_count                             D     C     Number of unicast packets that were sent
zhmc_nic_packets_received_count                         D     C     Number of unicast packets that were received
zhmc_nic_packets_sent_dropped_count                     D     C     Number of sent packets that were dropped (resource shortage)
zhmc_nic_packets_received_dropped_count                 D     C     Number of received packets that were dropped (resource shortage)
zhmc_nic_packets_sent_discarded_count                   D     C     Number of sent packets that were discarded (malformed)
zhmc_nic_packets_received_discarded_count               D     C     Number of received packets that were discarded (malformed)
zhmc_nic_multicast_packets_sent_count                   D     C     Number of multicast packets sent
zhmc_nic_multicast_packets_received_count               D     C     Number of multicast packets received
zhmc_nic_broadcast_packets_sent_count                   D     C     Number of broadcast packets sent
zhmc_nic_broadcast_packets_received_count               D     C     Number of broadcast packets received
zhmc_nic_data_sent_bytes                                D     G     Amount of data sent over the collection interval
zhmc_nic_data_received_bytes                            D     G     Amount of data received over the collection interval
zhmc_nic_data_rate_sent_bytes_per_second                D     G     Data rate sent over the collection interval
zhmc_nic_data_rate_received_bytes_per_second            D     G     Data rate received over the collection interval
======================================================  ====  ====  ==================================================================

Legend:

* Mode: The operational mode of the CPC: C=Classic, D=DPM
* Type: The Prometheus metric type: G=Gauge, C=Counter


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
      verify_cert: {verify-cert}

    extra_labels:  # optional
      # list of labels:
      - name: {extra-label-name}
        value: {extra-label-value}

Where:

* ``{hmc-ip-address}`` is the IP address of the HMC.

* ``{hmc-userid}`` is the userid on the HMC to be used for logging on.

* ``{hmc-password}`` is the password of that userid.

* ``{verify-cert}`` controls whether and how the HMC server certificate is
  verified. For details, see :ref:`HMC certificate`.

* ``{extra-label-name}`` is the label name.

* ``{extra-label-value}`` is the label value. The string value is used directly
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
          - name: {mg-label-name}
            value: {mg-label-value}

    metrics:
      # dictionary of metric groups:
      {hmc-metric-group}:

        # dictionary format for defining metrics:
        {hmc-metric}:
          exporter_name: {metric}_{unit}
          exporter_desc: {help}
          metric_type: {metric-type}
          percent: {percent-bool}
          valuemap: {valuemap}
          labels:
            # list of labels:
            - name: {m-label-name}
              value: {m-label-value}

        # list format for defining metrics:
        - property_name: {hmc-metric}                     # either this
          properties_expression: {properties-expression}  # or this
          exporter_name: {metric}_{unit}
          exporter_desc: {help}
          percent: {percent-bool}
          valuemap: {valuemap}
          labels:
            # list of labels:
            - name: {m-label-name}
              value: {m-label-value}

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

* ``{mg-label-name}`` is the label name at the metric group level.

* ``{mg-label-value}`` identifies where the label value is taken from, as follows:

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

  - ``{hmc-metric}`` the name of the HMC metric within the same metric
    group whose metric value should be used as a label value. This can be used
    to use accompanying HMC metrics that are actually identifiers for resources,
    a labels for the actual metric. Example: The HMC returns metrics group
    ``channel-usage`` with metric ``channel-usage`` that has the actual value
    and metric ``channel-name`` that identifies the channel to which the metric
    value belongs. The following fragment utilizes the ``channel-name`` metric
    as a label for the ``channel-usage`` metric:

* ``{m-label-name}``, ``{m-label-value}`` is the label name and value at the
  single metric level. The label names have specific meanings, and only the
  following label names are allowed:

  - ``value``: Indicates an alternative string-typed value to an interpreter of
    the Prometheus metric. Can only be used on resource-based metrics.

    ``{m-label-value}`` is the name of a property on the  HMC resource, and the
    label value shown in the Prometheus export is the property value. This is
    used for example for string-typed resource properties, where the Prometheus
    metric value shows the string value mapped to a floating point value, but
    the ``value`` label shows the original string value of the HMC resource
    property.

  - ``valuetype``: Indicates to an interpreter of the Prometheus metric that the
    floating point value of the Prometheus metric should be converted to a
    different datatype.

    ``{m-label-value}``) is the name of the datatype as follows:

    - ``bool``: The Prometheus metric value should be converted to a boolean,
      where 0.0 becomes False, and anything else becomes True.

    - ``int``: The Prometheus metric value should be converted to an integer
      that is the rounded metric value (i.e. not just cutting off the fractional
      part of the floating point number).

* ``{properties-expression}`` is a Jinja2 expression whose value should be used
  is as the metric value, for resource based metrics. The expression uses
  the variable ``properties`` which is the resource properties dictionary of the
  resource. The ``properties_expression`` attribute is mutually exclusive with
  ``property_name``.

* ``{metric-type}`` is an optional enum value that defines the Prometheus metric
  type used for this metric:
  - "gauge" (default) - For values that can go up and down
  - "counter" - For values that are monotonically increasing counters

* ``{percent-bool}`` is a boolean indicating whether the metric value should
  be divided by 100. The reason for this is that the HMC metrics represent
  percentages such that a value of 100 means 100% = 1, while Prometheus
  represents them such that a value of 1.0 means 100% = 1.

* ``{valuemap}`` is an optional dictionary for mapping string enumeration values
  in the original HMC value to integers to be exported to Prometheus. This is
  used for example for the processor mode (shared, dedicated).

* ``{metric}_{unit}`` is the Prometheus local metric name and unit in
  the full metric name ``zhmc_{resource-type}_{metric}_{unit}``.

* ``{help}`` is the description text that is exported as ``# HELP``.

Example for label definition at the metric group level using another metric

.. code-block:: yaml

    metric_groups:
      channel-usage:
        prefix: channel
        fetch: True
        labels:
          - name: cpc    # becomes e.g.: cpc="CPCA"
            value: resource
          - name: channel_css_chpid   # becomes e.g.: channel_css_chpid="CHAN01"
            value: channel-name
    metrics:
      channel-usage:
        channel-usage:
          percent: True
          exporter_name: usage_ratio
          exporter_desc: Usage ratio of the channel
          # This metric will have the labels defined in its metric group

Example for label definition at the single metric level specifying a different type:

.. code-block:: yaml

    metric_groups:
      cpc-resource:
        type: resource
        resource: cpc
        prefix: cpc
        fetch: true
        labels:
          - name: cpc    # becomes e.g.: cpc="CPCA"
            value: resource
    metrics:
      cpc-resource:
        - property_name: has-unacceptable-status
          exporter_name: has_unacceptable_status
          exporter_desc: Boolean indicating whether the CPC has an unacceptable status (0=false, 1=true)
          labels:
            - name: valuetype    # becomes: valuetype="bool"
              value: bool

Example for label definition at the single metric level specifying a string value:

.. code-block:: yaml

    metric_groups:
      logical-partition-resource:
        type: resource
        resource: cpc.logical-partition
        prefix: partition
        fetch: true
        labels:
          - name: cpc    # becomes e.g.: cpc="CPCA"
            value: resource.parent
          - name: partition    # becomes e.g.: partition="LPAR1"
            value: resource
    metrics:
      logical-partition-resource:
        - properties_expression: "{'operating': 0, 'not-operating': 1, 'not-activated': 2, 'exceptions': 10}.get(properties.status, 99)"
          exporter_name: lpar_status_int
          exporter_desc: "LPAR status as integer (0=operating, 1=not-operating, 2=not-activated, 10=exceptions, 99=unsupported value)"
          labels:
            - name: value   # becomes e.g. value="operating"
              value: status


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

The exporter supports logging its own activities and the interactions with the
HMC. By default, logging is disabled.

Logging is enabled by using the ``--log DEST`` option that controls the
logging destination as follows:

* ``--log stderr`` - log to the Standard Error stream
* ``--log syslog`` - log to the System Log (see :ref:`Logging to the System Log`)
* ``--log FILE`` - log to the log file with path name ``FILE``.

There are multiple components that can log. By default, all of them log at the
warning level. This can be fine tuned by using the ``--log-comp COMP[=LEVEL]``
option. This option can be specified multiple times, and the specified options
add in sequence to the default of ``all=warning``.

The components that can be specified in ``COMP`` are:

* ``exporter`` - activities of the exporter.
  Logger name: ``zhmcexporter``.
* ``hmc`` - HTTP interactions with the HMC performed by the zhmcclient library.
  Logger name: ``zhmcclient.hmc``.
* ``jms`` - JMS notifications from the HMC received by the zhmcclient library.
  Logger name: ``zhmcclient.jms``.
* ``all`` - all of these components.

The log levels that can be specified in ``LEVEL`` are:

* ``error`` - Show only errors for the component. Errors are serious conditions
  that need to be fixed by the user. Some errors may need to be reported as
  issues. The exporter retries with the HMC in case of certain errors, but some
  errors cause the exporter to terminate.
* ``warning`` - Show errors and warnings for the component. Warnings never cause
  the exporter to terminate, but should be analyzed and may need to be fixed.
* ``info`` - Show informations, warnings and errors for the component.
  Informations are useful to understand what is going on.
* ``debug`` - Show debug info, informations, warnings and errors for the
  component. Debug info provides a very detailed amount of information that may
  be useful foo analyzing problems.
* ``off`` - Show no log messages for the component.

The ``LEVEL`` part can be omitted in the ``--log-comp`` option, and its
default is ``warning``. This is for compatibility with older versions of the
exporter.

The default log level for each component is ``warning``, and specifying
other log levels changes that level only for the specified components but
keeps the default for those components that are not specified.

Examples:

.. code-block:: bash

    # log to Standard Error with all=warning
    $ zhmc_prometheus_exporter --log stderr ...

    # log to file mylog.log with all=warning
    $ zhmc_prometheus_exporter --log mylog.log ...

    # log to file mylog.log with exporter=info, hmc=warning (by default), jms=warning (by default)
    $ zhmc_prometheus_exporter --log mylog.log --log-comp exporter=info

    # log to file mylog.log with exporter=info, hmc=warning (by default), jms=debug
    $ zhmc_prometheus_exporter --log mylog.log --log-comp exporter=info --log-comp jms=debug

    # log to file mylog.log with exporter=debug, hmc=debug, jms=debug
    $ zhmc_prometheus_exporter --log mylog.log --log-comp all=debug

    # log to file mylog.log with exporter=info, hmc=off, jms=off
    $ zhmc_prometheus_exporter --log mylog.log --log-comp all=off --log-comp exporter=info


Logging to the System Log
^^^^^^^^^^^^^^^^^^^^^^^^^

When logging to the System Log, the syslog address used by the exporter
depends on the operating system as follows:

* Linux: ``/dev/log``
* macOS: ``/var/run/syslog``
* Windows: UDP port 514 on localhost (requires a syslog demon to run)
* CygWin: ``/dev/log`` (requires the syslog-ng package to be installed)

For other operating systems, UDP port 514 on localhost is used.

Messages logged to the system log will only show up there if the syslog
configuration has enabled the syslog facility and the syslog severity levels
that are used by the exporter.
The configuration of the syslog depends on the operating system or syslog demon
that is used and is therefore not described here.

The syslog facility that will be used by the exporter can be specified with the
``--syslog-facility`` option and defaults to ``user``.

The syslog severity levels (not to be confused with syslog priorities) that will
be used by the exporter are derived from the Python log levels using the default
mapping defined by Python logging, which is:

================  =================
Python log level  Syslog severity
================  =================
``ERROR``         3 (Error)
``WARNING``       4 (Warning)
``INFO``          6 (Informational)
``DEBUG``         7 (Debug)
================  =================

On some systems, the syslog rejects messages that exceed a certain limit.
For this reason, the exporter truncates the message text to somewhat below
2048 Bytes, when logging to the system log. Messages are not truncated when
logging to the Standard Error stream or to a file.


Performance
-----------

The support for resource property based metric values that was introduced in
version 1.0 has slowed down the startup of the exporter quite significantly if
these metrics are enabled.

Here is an elapsed time measurement for the startup of the exporter using an HMC
in one of our development data centers:

* 11:33 min for preparing auto-update for 143 partitions on two z14 systems in classic mode
* 0:12 min for preparing auto-update for 98 partitions on two z13 systems in DPM mode
* 1:30 min for preparing auto-update for the 4 CPCs
* 10:25 min for all other startup activities (without the
  partition-attached-network-interface metrics group that would have been 0:48 min)

Once the exporter is up and running, the fetching of metrics by Prometheus from
the exporter is very fast:

* 0:00.35 min (=350 ms) for fetching metrics with 236 HELP/TYPE lines and 5269
  metric value lines (size: 500 KB)

In this measurement, the complete set of metrics was enabled for the 4 CPCs
described above.

This result includes metric values from properties of auto-updated resources
(which are maintained in the exporter and are updated asynchronously via
notifications the exporter receives from the HMC) and metric values retrieved
from the HMC metric service by executing a single HMC operation
("Get Metric Context").

This was measured with a local web browser that was directed to an exporter
running on the same local system (a MacBook Pro). The network path between the
exporter and the targeted HMC went via VPN to the IBM Intranet (via WLAN and
Internet) and then across a boundary firewall.
