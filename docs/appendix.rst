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


Troubleshooting
---------------

The `zhmcclient Troubleshooting <https://python-zhmcclient.readthedocs.io/en/latest/appendix.html#troubleshooting>`_
section also applies to the exporter project.

There are no additional exporter-specific troubleshooting hints at the moment.


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

   Jinja2 expression
     A Jinja2 expression *without* surrounding double curly braces.

     See https://jinja.palletsprojects.com/en/3.1.x/templates/#expressions
     for a description.

     When putting Jinja2 expressions into YAML files, it is recommended to put
     the expression into double or single quotes to protect it from being
     interpreted as YAML. An example where that makes a difference is a
     Jinja2 expression that is a literal string: The Jinja2 expression ``'abc'``
     must be put into double quotes in YAML to protect the single quotes and
     becomes ``value: "'abc'"``.

   Metric service based metrics
     Metrics that are retrieved from the HMC using the "Get Metric Context"
     operation. For more details, see :ref:`Available metrics`.

   Resource property based metrics
     Metrics that are obtained from properties of HMC resources.
     For more details, see :ref:`Available metrics`.

Bibliography
------------

.. glossary::

   HMC API
       The Web Services API of the z Systems Hardware Management Console, described in the following books:

   HMC API 2.11.1
       `IBM SC27-2616, System z Hardware Management Console Web Services API (Version 2.11.1) <https://www.ibm.com/support/pages/node/6017542>`_

   HMC API 2.12.0
       `IBM SC27-2617, System z Hardware Management Console Web Services API (Version 2.12.0) <https://www.ibm.com/support/pages/node/6019030>`_

   HMC API 2.12.1
       `IBM SC27-2626, System z Hardware Management Console Web Services API (Version 2.12.1) <https://www.ibm.com/support/pages/node/6017614>`_

   HMC API 2.13.0
       `IBM SC27-2627, z Systems Hardware Management Console Web Services API (Version 2.13.0) <https://www.ibm.com/support/pages/node/6018628>`_

   HMC API 2.13.1
       `IBM SC27-2634, z Systems Hardware Management Console Web Services API (Version 2.13.1) <https://www.ibm.com/support/pages/node/6019732>`_

   HMC API 2.14.0
       `IBM SC27-2636, IBM Z Hardware Management Console Web Services API (Version 2.14.0) <https://www.ibm.com/support/pages/node/6020008>`_

   HMC API 2.14.1
       `IBM SC27-2637, IBM Z Hardware Management Console Web Services API (Version 2.14.1) <https://www.ibm.com/support/pages/node/6019768>`_

   HMC API 2.15.0
       `IBM SC27-2638, IBM Z Hardware Management Console Web Services API (Version 2.15.0) <https://www.ibm.com/support/pages/node/6019720>`_
       (covers both GA1 and GA2)

   HMC Security
       `Hardware Management Console Security <https://www.ibm.com/support/pages/node/6017320>`_
