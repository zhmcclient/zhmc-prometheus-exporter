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

.. _IBM Z: https://www.ibm.com/products/z?lnk=flatitem
.. _Prometheus exporter: https://prometheus.io/docs/instrumenting/exporters/
.. _Prometheus: https://prometheus.io


Supported environments
----------------------

* Operating systems: Linux, macOS, Windows
* Python versions: 3.8 and higher
* HMC versions: 2.11.1 and higher


Reporting issues
----------------

If you encounter a problem, please report it as an `issue on GitHub`_.

.. _issue on GitHub: https://github.com/zhmcclient/zhmc-prometheus-exporter/issues

License
-------

This package is licensed under the `Apache 2.0 License`_.

.. _Apache 2.0 License: https://apache.org/licenses/LICENSE-2.0
