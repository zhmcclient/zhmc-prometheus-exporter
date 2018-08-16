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

.. image:: https://travis-ci.org/zhmcclient/zhmc-prometheus-exporter.svg?branch=master
    :target: https://travis-ci.org/zhmcclient/zhmc-prometheus-exporter

A `prometheus.io`_ exporter written in Python for metrics from the `IBM Z`_ Hardware Management Console using `zhmcclient`_. Tested with Python 3.4 through 3.7.

.. _prometheus.io: https://prometheus.io/
.. _IBM Z: https://www.ibm.com/it-infrastructure/z
.. _zhmcclient: https://github.com/zhmcclient/python-zhmcclient

Installation
------------

.. code-block:: bash

  $ pip3 install .

Quickstart
----------

The exporter itself
^^^^^^^^^^^^^^^^^^^

Set up your exporter. Edit your credentials YAML file. A `sample credentials YAML`_ is provided. Enter the IP address of the HMC, your username, and your password there. You can then run

.. code-block:: bash

  $ zhmc_prometheus_exporter -c samplecreds.yaml -m metrics.yaml

where ``metrics.yaml`` defines the metrics and descriptions. You do not have to edit ``metrics.yaml``. The default port is 9291, you can change it with ``-p``.

.. _sample credentials YAML: examples/samplecreds.yaml

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

* Create the dashboard in Grafana. A `sample JSON`_ is provided.

.. _sample JSON: examples/grafana.json

The following image illustrates what the setup described above could look like.

.. image:: examples/Deployment.png
    :align: center
    :alt: Deployment diagram of the example
