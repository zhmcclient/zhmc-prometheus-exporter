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

The `zhmcclient Troubleshooting <https://python-zhmcclient.readthedocs.io/en/stable/appendix.html#troubleshooting>`_
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

     See https://jinja.palletsprojects.com/en/stable/templates/#expressions
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
       `IBM SC27-2646-00, IBM Z Hardware Management Console Web Services API (Version 2.17.0) <https://www.ibm.com/docs/ko/module_1721331501652/pdf/SC27-2646-00.pdf>`_

   HMC Security
       `IBM SC28-7061-00, IBM Z Hardware Management Console Security (Version 2.17.0) <https://www.ibm.com/docs/ko/module_1721331501652/pdf/SC28-7061-00.pdf>`_

   HMC Help
       `IBM Z Hardware Management Console Help (Version 2.17.0) <https://www.ibm.com/docs/en/help-ibm-hmc-z17>`_
