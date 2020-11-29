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

Appendix
========

Glossary
--------

.. glossary::

   Exporter
      A server application for exposing metrics to Prometheus

   IBM Z
      IBM's mainframe product line

   Prometheus
      A server application for monitoring and alerting

   Z HMC
      Hardware Management Console for IBM Z

.. _`sample credentials YAML`:

Sample HMC credentials file
---------------------------

The following is a sample HMC credentials file (``hmccreds.yaml``).

The file is also available in the Git repo as
`examples/hmccreds.yaml <https://github.com/zhmcclient/zhmc-prometheus-exporter/blob/master/examples/hmccreds.yaml>`_.

.. literalinclude:: ../examples/hmccreds.yaml
  :language: yaml

.. _`sample metrics YAML`:

Sample metric definition file
-----------------------------

The following is a sample metric definition file (``metrics.yaml``) that lists
all metrics as of HMC 2.14 and that has some DPM metrics enabled.

The file is also available in the Git repo as
`examples/metrics.yaml <https://github.com/zhmcclient/zhmc-prometheus-exporter/blob/master/examples/metrics.yaml>`_.

.. literalinclude:: ../examples/metrics.yaml
  :language: yaml
