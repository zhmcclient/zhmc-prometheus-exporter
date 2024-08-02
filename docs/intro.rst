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

Introduction
============

What this package provides
--------------------------

The **IBM Z HMC Prometheus Exporter** is a `Prometheus exporter`_ written in
Python that retrieves metrics from the `IBM Z`_ Hardware Management Console (HMC)
and exports them to the `Prometheus`_ monitoring system.

The exporter supports all metrics provided by the Z HMC and in addition a number
of useful metrics that are based on properties of HMC resources (e.g. memory or
CPU weight of LPARs). The resource property based metrics are obtained in the
background via change notifications emitted by the HMC and via asynchronous
retrieval for properties where change notifications are not supported. This
keeps the time for providing the metric data to Prometheus short (sub-second to
a few seconds).

The exporter attempts to stay up as much as possible, for example it performs
automatic session renewals with the HMC if the logon session expires, and it
survives HMC reboots and automatically picks up metrics collection again once
the HMC come back up.

The exporter supports HTTP and HTTPS (with and without mutual TLS) for
Prometheus.

.. _IBM Z: https://www.ibm.com/it-infrastructure/z
.. _Prometheus exporter: https://prometheus.io/docs/instrumenting/exporters/
.. _Prometheus: https://prometheus.io

Supported environments
----------------------

* Operating systems: Linux, macOS, Windows
* Python versions: 3.8 and higher
* HMC versions: 2.11.1 and higher

Quickstart
----------

* Install the exporter and all of its Python dependencies as follows:

  .. code-block:: bash

      $ pip install zhmc-prometheus-exporter

  Note that an installation of Python packages using `setup.py install` is no
  longer recommended by the Python packaging community. For details, see
  https://blog.ganssle.io/articles/2021/10/setup-py-deprecated.html.
  Installation with `setup.py install` is no longer supported by this package.

* Provide a *config file* for use by the exporter.

  The exporter config file tells the exporter which HMC to talk to for
  obtaining metrics, and which userid and password to use for logging on to
  the HMC.

  It also defines whether HTTP or HTTPS is used for Prometheus, and HTTPS
  related certificates and keys.

  Finally, it defines which metric groups to fetch and to provide to
  Prometheus.

  Download the
  `sample exporter config file <https://github.com/zhmcclient/zhmc-prometheus-exporter/blob/master/examples/config.yaml>`_
  as ``config.yaml`` and edit that copy accordingly.

  For details, see :ref:`Exporter config file`.

* Run the exporter as follows:

  .. code-block:: bash

      $ zhmc_prometheus_exporter -c config.yaml
      Exporter is up and running on port 9291

  Depending on the number of CPCs managed by your HMC, and dependent on how many
  metrics are enabled, it will take some time until the exporter reports to be
  up and running. You can see what it does in the mean time by using the ``-v``
  option. Subsequent requests to the exporter will be sub-second.

* Direct your web browser at http://localhost:9291 (or https://localhost:9291
  when using HTTPS) to see the exported Prometheus metrics. Refreshing the
  browser will update the metrics.

Reporting issues
----------------

If you encounter a problem, please report it as an `issue on GitHub`_.

.. _issue on GitHub: https://github.com/zhmcclient/zhmc-prometheus-exporter/issues

License
-------

This package is licensed under the `Apache 2.0 License`_.

.. _Apache 2.0 License: http://apache.org/licenses/LICENSE-2.0
