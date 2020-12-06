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

IBM Z HMC Prometheus Exporter
=============================

.. image:: https://img.shields.io/pypi/v/zhmc-prometheus-exporter.svg
    :target: https://pypi.python.org/pypi/zhmc-prometheus-exporter/
    :alt: Version on Pypi

.. image:: https://github.com/zhmcclient/zhmc-prometheus-exporter/workflows/test/badge.svg?branch=master
    :target: https://github.com/zhmcclient/zhmc-prometheus-exporter/actions?query=branch%3Amaster
    :alt: Test status (master)

.. image:: https://readthedocs.org/projects/zhmc-prometheus-exporter/badge/?version=latest
    :target: https://readthedocs.org/projects/zhmc-prometheus-exporter/builds/
    :alt: Docs status (master)

.. image:: https://coveralls.io/repos/github/zhmcclient/zhmc-prometheus-exporter/badge.svg?branch=master
    :target: https://coveralls.io/github/zhmcclient/zhmc-prometheus-exporter?branch=master
    :alt: Test coverage (master)

The **IBM Z HMC Prometheus Exporter** is a `Prometheus exporter`_ written in
Python that retrieves metrics from the `IBM Z`_ Hardware Management Console (HMC)
and exports them to the `Prometheus`_ monitoring system.

.. _IBM Z: https://www.ibm.com/it-infrastructure/z
.. _Prometheus exporter: https://prometheus.io/docs/instrumenting/exporters/
.. _Prometheus: https://prometheus.io

Documentation
-------------

* `Documentation`_
* `Change log`_

.. _Documentation: https://zhmc-prometheus-exporter.readthedocs.io/en/stable/
.. _Change log: https://zhmc-prometheus-exporter.readthedocs.io/en/stable/changes.html

Quickstart
----------

* Install the exporter and all of its Python dependencies as follows:

  .. code-block:: bash

      $ pip install zhmc-prometheus-exporter

* Provide an *HMC credentials file* for use by the exporter.

  The HMC credentials file tells the exporter which HMC to talk to for
  obtaining metrics, and which userid and password to use for logging on to
  the HMC.

  Download the `sample HMC credentials file`_ as ``hmccreds.yaml`` and edit
  that copy accordingly.

  For details, see `HMC credentials file`_.

.. _HMC credentials file: https://zhmc-prometheus-exporter.readthedocs.io/en/stable/usage.html#hmc-credentials-file
.. _sample HMC credentials file: https://zhmc-prometheus-exporter.readthedocs.io/en/stable/usage.html#sample-hmc-credentials-file

* Provide a *metric definition file* for use by the exporter.

  The metric definition file maps the metrics returned by the HMC to metrics
  exported to Prometheus.

  Furthermore, the metric definition file allows optimizing the access time to
  the HMC by disabling the fetching of metrics that are not needed.

  Download the `sample metric definition file`_ as ``metrics.yaml``. It can
  be used as it is and will have all metrics enabled and mapped properly. You
  only need to edit the file if you want to adjust the metric names, labels, or
  metric descriptions, or if you want to optimize access time by disabling
  metrics not needed.

  For details, see `Metric definition file`_.

.. _Metric definition file: https://zhmc-prometheus-exporter.readthedocs.io/en/stable/usage.html#metric-definition-file
.. _sample metric definition file: https://zhmc-prometheus-exporter.readthedocs.io/en/stable/usage.html#sample-metric-definition-file

* Run the exporter as follows:

  .. code-block:: bash

      $ zhmc_prometheus_exporter -c hmccreds.yaml -m metrics.yaml

* Direct your web browser at http://localhost:9291 to see the exported
  Prometheus metrics (depending on the number of CPCs managed by your HMC, and
  dependent on how many metrics are enabled, this may take a moment).

Reporting issues
----------------

If you encounter a problem, please report it as an `issue on GitHub`_.

.. _issue on GitHub: https://github.com/zhmcclient/zhmc-prometheus-exporter/issues

License
-------

This package is licensed under the `Apache 2.0 License`_.

.. _Apache 2.0 License: http://apache.org/licenses/LICENSE-2.0
