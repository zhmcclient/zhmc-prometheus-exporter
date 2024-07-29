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

Trouble shooting
================

This section describes some issues and how to resolve them. If you encounter
an issue that is not covered here, see :ref:`Reporting issues`.

Permission error with exporter config file
------------------------------------------

Example:

.. code-block:: bash

  $ zhmc_prometheus_exporter
  Error: Permission error reading exporter config file ...

You don't have permission to read from the exporter config file. Change the
permissions with ``chmod``, check ``man chmod`` if you are unfamiliar with it.

Exporter config file not found
------------------------------

Example:

.. code-block:: bash

    $ zhmc_prometheus_exporter
    Error: Cannot find exporter config file ...

The exporter config file does not exist.

You need to create an exporter config file as described in :ref:`Quickstart`.

YAML syntax error in exporter config file
-----------------------------------------

Example:

.. code-block:: bash

    $ zhmc_prometheus_exporter
    Error: YAML error reading exporter config file ...

The exporter config file breaks the syntax rules of the YAML specification.

Compare your exporter config file with the sample exporter config file from the
``examples`` folder, see :ref:`Quickstart` for more information.
You can also check the `YAML specification`_.

.. _Quickstart: ./intro.rst#quickstart
.. _YAML specification: http://yaml.org/spec/1.2/spec.html

YAML validation error in exporter config file
---------------------------------------------

Example:

.. code-block:: bash

    $ zhmc_prometheus_exporter
    Error: Validation of exporter config file ... failed on ...

There are additional elements in the exporter config file, or required elements
are missing, or other validation rules are violated.
Compare your exporter config file with the sample exporter config file from the
``examples`` folder, see :ref:`Quickstart` for more information.

Timeout
-------

Example:

.. code-block:: bash

    $ zhmc_prometheus_exporter
    Error: Connection error ...: Max retries exceeded ... Connection to ... timed out.

Ensure that you have network connectivity to the HMC that is specified in the
exporter config file.

Authentication error
--------------------

Example:

.. code-block:: bash

    $ zhmc_prometheus_exporter
    Error: Authentication error returned from the HMC at ... HTTP authentication failed with 403,0: Login failed

Wrong username or password in the exporter config file. Check if you can
access the HMC with this username-password combination.

Warning: Skipping metric or metric group
----------------------------------------

Example:

.. code-block:: bash

    $ zhmc_prometheus_exporter
    ...: UserWarning: Skipping metric group 'new-metric-group' returned by the HMC that is
      not defined in the 'metric_groups' section of metric definition file metrics.yaml
      warnings.warn(warning_str % (metric, filename))

    $ zhmc_prometheus_exporter
    ...: UserWarning: Skipping metric 'new-metric' of metric group 'new-metric-group'
      returned by the HMC that is not defined in the 'metrics' section of metric
      definition file metrics.yaml
      warnings.warn(warning_str % (metric, filename))

If the HMC implements new metrics, or if the metric definition file misses a
metric or metric group, the exporter issues this warning to make you aware
of that.
