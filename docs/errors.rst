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

Error messages
==============

This page further describes error messages if you have trouble understanding them. If an error is not listed here, see :ref:`Reporting issues`.

Permission error
----------------

Example:

.. code-block:: bash

  $ zhmc_prometheus_exporter
  Permission error. Make sure you have appropriate permissions to read from /etc/zhmc-prometheus-exporter/hmccreds.yaml.

You don't have permission to read from a YAML file. Change the permissions with ``chmod``, check ``man chmod`` if you are unfamiliar with it.

File not found
--------------

Example:

.. code-block:: bash

  $ zhmc_prometheus_exporter
  Error: File not found. It seems that /etc/zhmc-prometheus-exporter/hmccreds.yaml does not exist.

A required YAML file (``hmccreds.yaml`` and ``metrics.yaml``) does not exist. Make sure that you specify paths, relative or absolute, with ``-c`` or ``-m`` if the file is not in ``etc/zhmc-prometheus-exporter/``. You have to copy the credentials file from the ``examples`` folder and fill in your own credentials, see :ref:`Quickstart` for more information.

Section not found
-----------------

Example:

.. code-block:: bash

  $ zhmc_prometheus_exporter
  Section metric_groups not found in file /etc/zhmc-prometheus-exporter/metrics.yaml.

At least one of the sections ``metric_groups`` and ``metrics`` in your ``metrics.yaml`` or ``metrics`` in ``hmccreds.yaml`` is missing in its entirety. See chapter :ref:`The metrics YAML file` for more information.

Doesn't follow the YAML syntax
------------------------------

Example:

.. code-block:: bash

  $ zhmc_prometheus_exporter
  /etc/zhmc-prometheus-exporter/metrics.yaml does not follow the YAML syntax

A YAML file you specified breaks the syntax rules of the YAML specification. If you derive your YAML files from the existing examples (see chapter :ref:`Quickstart`), this error should not occur, you can also check the `YAML specification`_.

.. _Quickstart: ./intro.rst#quickstart
.. _YAML specification: http://yaml.org/spec/1.2/spec.html

You did not specify
-------------------

Example:

.. code-block:: bash

  $ zhmc_prometheus_exporter
  You did not specify the IP address of the HMC in /etc/zhmc-prometheus-exporter/hmccreds.yaml.

There is a lot of mandatory information in the two YAML files that might be missing if you improperly filled the credentials file (see :ref:`Quickstart`) or made bad changes to the metrics file (see :ref:`The metrics YAML file`).

All of these values could in some way be missing or incorrect:

**In the credentials YAML file, in the section "metrics"**

* ``hmc``, the IP address of the HMC (it must be a correct IP address as well!)
* ``userid``, a username for the HMC
* ``password``, the respective password

**In the metrics YAML file, in the section "metric_groups", for each metric group**

* ``prefix``, the prefix for the metrics to be exported
* ``fetch``, specifying whether the group should be fetched (it must be one of ``True`` or ``False`` as well!)

**In the metrics YAML file, in the section "metrics", for each metric group**

* The group must also exist in the ``metric_groups`` section
* ``percent``, specifying whether the metric is a percent value (it must be one of ``True`` or ``False`` as well!)
* ``exporter_name``, the name for the exporter (minus the prefix)
* ``exporter_desc``, the mandatory description for the exporter

Time out
--------

Example:

.. code-block:: bash

  $ zhmc_prometheus_exporter
  Time out. Ensure that you have access to the HMC and that you have stored the correct IP address in /etc/zhmc-prometheus-exporter/hmccreds.yaml.

There is a certain timeout threshold if the HMC cannot be found. Check that you have access to the HMC on the IP address that you specified in the credentials file.

Authentication error
--------------------

Example:

.. code-block:: bash

  $ zhmc_prometheus_exporter
  Authentication error. Ensure that you have stored a correct user ID-password combination in /etc/zhmc-prometheus-exporter/hmccreds.yaml.

Wrong username or password in the credentials file. Check if you can regularly access the HMC with this username-password combniation.

Warning: Metric not found
-------------------------

Example:

.. code-block:: bash

  $ zhmc_prometheus_exporter
  ...: UserWarning: Metric network-usage was not found. Consider adding it to your metrics.yaml.
    warnings.warn(warning_str % (metric, filename))

It might occur that within a known metric group, the HMC exposes a metric previously unknown. Some generic formatting will automatically be added, but it is recommended that you actually edit this metric in.
