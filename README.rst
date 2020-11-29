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

zhmc-prometheus-exporter
========================

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


A `prometheus.io`_ exporter written in Python for metrics from the `IBM Z`_ Hardware Management Console using `zhmcclient`_. Tested with Python 3.4 through 3.7.

.. _prometheus.io: https://prometheus.io/
.. _IBM Z: https://www.ibm.com/it-infrastructure/z
.. _zhmcclient: https://github.com/zhmcclient/python-zhmcclient

Installation
------------

.. code-block:: bash

  $ pip3 install zhmc-prometheus-exporter

Documentation
-------------

`Read the Docs`_

.. _Read the Docs: https://zhmc-prometheus-exporter.readthedocs.io/en/stable/


Quickstart
----------

The exporter itself
^^^^^^^^^^^^^^^^^^^

Set up your exporter as follows:

Edit your HMC credentials YAML file ``hmccreds.yaml``. A sample
`hmccreds.yaml <https://github.com/zhmcclient/zhmc-prometheus-exporter/blob/master/examples/hmccreds.yaml>`_
file is provided in the Git repo.
Enter the IP address of the HMC, your username, and your password there.

Get your metric definition file ``metrics.yaml``. A sample
`metrics.yaml <https://github.com/zhmcclient/zhmc-prometheus-exporter/blob/master/examples/metrics.yaml>`_
file is provided in the Git repo.
The sample file defines some DPM related metrics to be enabled. If your system
is in DPM mode, you do not need to edit the sample file.

Put the ``hmccreds.yaml`` file and the ``metrics.yaml`` file
into ``/etc/zhmc-prometheus-exporter/``.

You can then run

.. code-block:: bash

  $ zhmc_prometheus_exporter

The default port is 9291, you can change it with ``-p``. If you do not want to put ``hmccreds.yaml`` and ``metrics.yaml`` into ``/etc/zhmc-prometheus-exporter``, you can also specify them with ``-c`` and ``-m`` respectively.

Demo setup
^^^^^^^^^^

If you want a quick "three simple metrics" setup with Prometheus and Grafana you can proceed as follows:

* Set up a Prometheus server. Get it from `Prometheus`_. A `sample configuration YAML`_ is provided. Fill in the IP and port the exporter will run on. If you left it at default, the port will be 9291. You can then run::

    $ ./prometheus --config.file=prometheus.yaml

  See also `Prometheus' guide`_.

.. _Prometheus: https://prometheus.io/download/
.. _sample configuration YAML: examples/prometheus.yaml
.. _Prometheus' guide: https://prometheus.io/docs/prometheus/latest/getting_started/

* Set up a Grafana server. Get it from `Grafana`_. You can then run::

    $ ./bin/grafana-server web

  By default it will be on ``localhost:3000``. You will have to set IP and port of the Prometheus server. If you didn't change it, it's ``localhost:9090``. See also `Prometheus' guide on Grafana`_.

.. _Grafana: https://grafana.com/grafana/download
.. _Prometheus' guide on Grafana: https://prometheus.io/docs/visualization/grafana/

* Create the dashboard in Grafana. A `sample JSON`_ is provided. If you want it to work natively, you will have to name your source ``ZHMC_Prometheus``.

.. _sample JSON: examples/grafana.json

The following image illustrates what the setup described above could look like.

.. image:: https://github.com/zhmcclient/zhmc-prometheus-exporter/blob/master/docs/deployment.png?raw=true
    :align: center
    :alt: Deployment diagram of the example
