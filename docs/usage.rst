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

This page describes how to use the exporter beyond following the quickstart guide.

Revision: Quickstart
--------------------

To sign into the HMC, you have to provide credentials in the YAML format. The file ``hmccreds.yaml`` could look something like this (see also the sample in the examples folder):

.. code-block:: yaml

  metrics:
    hmc: 10.10.10.10
    userid: user
    password: password

Furthermore, the file ``metrics.yaml`` defines details about the metrics fetching. An example file is in the repository root, for more information on its anatomy see chapter :ref:`The metrics YAML file`.

Put both of these files into ``/etc/zhmc-prometheus-exporter`` (or link them). You can then run

.. code-block:: bash

  $ zhmc_prometheus_exporter

The default port is 9291, you can change it with ``-p``. If you do not want to put ``hmccreds.yaml`` and ``metrics.yaml`` into ``/etc/zhmc-prometheus-exporter``, you can also specify them with ``-c`` and ``-m`` respectively.

Output anatomy
--------------

All metrics are of the Prometheus specific type Gauge. They are grouped into prefixes, e.g. ``dpm`` for general metrics read in the Dynamic Partition Manager (DPM) mode, or ``lpar`` for logical partitions in classic mode. The suffix of a metric represents the unit of measurement; for instance, a percent value will usually end with ``usage_ratio``, while a temperature would end in ``celsius``.

In the case of many of the metrics, they apply to multiple devices. The ``dpm`` group can have several CPCs, the ``partition`` group will usually have several partitions, etc. These devices are separated with labels, the label being ``resource`` and the value being the CPC name, the partition name, etc.

Available metrics
-----------------
This is an easier to read version of the relevant parts from the `HMC Web Services API Documentation`_. On the first level, you can read the metric groups and their prefixes. They will additionally be prefixed with ``zhmc_``. On the second level, you can read the metrics and their exporter name without the prefix.

**Only in classic mode**

* cpc-usage-overview as ``cpc``
* logical-partition-usage as ``lpar``
* channel-usage as ``channel``

**Only in DPM mode**

* dpm-system-usage-overview as ``dpm``

  - network-usage as ``network_usage_ratio``
  - temperature-celsius as ``temperature_celsius``
  - storage-usage as ``storage_usage_ratio``
  - crypto-usage as ``crypto_usage_ratio``
  - processor-usage as ``processor_usage_ratio``
  - accelerator-usage as ``accelerator_usage_ratio``
  - all-shared-processor-usage as ``shared_processor_usage_ratio``
  - power-consumption-watts as ``power_watts``
  - ifl-shared-processor-usage as ``ifl_shared_processor_usage_ratio``
  - ifl-all-processor-usage as ``ifl_total_processor_usage_ratio``
  - cp-shared-processor-usage as ``cp_shared_usage_ratio``
  - cp-all-processor-usage as ``cp_total_usage_ratio``
* partition-usage as ``partition``

  - accelerator-usage as ``accelerator_usage_ratio``
  - crypto-usage as ``crypto_usage_ratio``
  - network-usage as ``network_usage_ratio``
  - processor-usage as ``processor_usage_ratio``
  - storage-usage as ``storage_usage_ratio``
* adapter-usage as ``adapter``
* crypto-usage as ``crypto``
* flash-memory-usage as ``flash``
* roce-usage as ``roce``

**Only in ensemble mode**

* virtualization-host-cpu-memory-usage as ``virtualized``

.. _HMC Web Services API Documentation: https://www-01.ibm.com/support/docview.wss?uid=isg2db4805ce05eea3dd85258194006a371e

The metrics YAML file
---------------------

Various properties about scraping are collected from the ``metrics.yaml`` file that is given to the exporter with the ``-m`` option.

The metric groups section
^^^^^^^^^^^^^^^^^^^^^^^^^

contains the metric groups, as seen on the first level of the lists in :ref:`Available metrics`.

Example:

.. code-block:: yaml

  dpm-system-usage-overview:
    prefix: dpm
    fetch: True

Within one section, the metric prefix and the fetch True/False value is stored. Note that the former will additionally be prefixed with ``zhmc_``. The latter is due to runtime concerns: Some metric groups take over a second to be scraped.

The metrics section
^^^^^^^^^^^^^^^^^^^

contains the metrics themselves, as seen on the second level of the lists in :ref:`Available metrics`.

Example:

.. code-block:: yaml

  dpm-system-usage-overview:
    network-usage:
      percent: True
      exporter_name: network_usage_ratio
      exporter_desc: DPM total network usage

The first level section is the metric group, the second level section is the metric. Within one metric section, a percent True/False value is stored, as well as the name and description for the exporter. The former is required because for the HMC, 100% means 100, whereas for Prometheus, 100% means 1. The latter two are requirements for an exporter, the ``exporter_name`` will be prepended with the group prefix and an underscore.
