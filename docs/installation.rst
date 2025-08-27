.. Copyright 2018,2025 IBM Corp. All Rights Reserved.
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

Installation
============

This section describes how to install the exporter, create the
exporter config file, and set up the HMC.

.. _virtual Python environment: https://docs.python-guide.org/dev/virtualenvs/
.. _Pypi: https://pypi.org/


Steps
-----

The installation steps are described using Unix/Linux/macOS commands. When
installing on Windows, use the equivalent Windows commands (e.g. "md" instead of
"mkdir").

1.  Install the zhmc-prometheus-exporter Python package using any of the following
    approaches:

    * :ref:`Installation using pipx` (recommended approach)
    * :ref:`Installation into a virtual Python environment`
    * :ref:`Installation into a system Python`
    * :ref:`Installation on a system without Internet access`

    You can verify that the exporter and its dependent packages are installed
    correctly by invoking:

    .. code-block:: bash

        $ zhmc_prometheus_exporter --version
        zhmc_prometheus_exporter version: 2.0.1
        zhmcclient version: 1.21.0
        prometheus_client (vendored) version: 0.20.0.post1

2.  Create the exporter config file.

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

3.  Make sure the HMC is set up correctly.

    * The Web Services API is enabled on the HMC
    * The HMC has a certificate installed
    * The HMC userid has permission for the Web Services API
    * The HMC userid has the required object and task permissions

4.  Make sure the HMC can be reached from the system that runs the exporter.

    When using firewalls or proxies, see :ref:`Setting up firewalls or proxies`.

5.  Run the exporter as follows:

    .. code-block:: bash

        $ zhmc_prometheus_exporter -c config.yaml
        Exporter is up and running on port 9291

    Depending on the number of CPCs managed by your HMC, and dependent on how many
    metrics are enabled, it will take some time until the exporter reports to be
    up and running. You can see what it does in the mean time by using the ``-v``
    option. Subsequent requests to the exporter will be sub-second.

    Running the exporter in a container is described in
    :ref:`Running in a Docker container`.

6.  Direct your web browser at http://localhost:9291 (or https://localhost:9291
    when using HTTPS) to see the exported Prometheus metrics. Refreshing the
    browser will update the metrics.

Installation using pipx
-----------------------

The recommended way to install the exporter is by using pipx.

Pipx creates a `virtual Python environment`_ under the covers, installs the
Python package into that environment and makes the ``zhmc_prometheus_exporter``
command available in a directory that is in the PATH.
The ``zhmc_prometheus_exporter`` command will be available that way, regardless
of whether or not you have a virtual Python environment active (that you may
need for other purposes).

1.  Prerequisite: Install pipx as an OS-level package

    Follow the steps at https://pipx.pypa.io/stable/installation/ to install
    pipx as an OS-level package to your local system.

2.  Install the exporter using pipx

    To install the latest released version of the exporter:

    .. code-block:: bash

        $ pipx install zhmc-prometheus-exporter

    To install a specific released version of the exporter, e.g. 1.7.1:

    .. code-block:: bash

        $ pipx install zhmc-prometheus-exporter==1.7.1

    To install a specific development branch of the exporter, e.g. master:

    .. code-block:: bash

        $ pipx install git+https://github.com/zhmcclient/zhmc-prometheus-exporter.git@master

    To install the exporter with a non-default Python version, e.g. 3.10:

    .. code-block:: bash

        $ pipx install zhmc-prometheus-exporter --python python3.10

Installation into a virtual Python environment
----------------------------------------------

In some cases it may be useful to install the exporter into your own
`virtual Python environment`_. That avoids the dependency to pipx, but it
requires you to activate the virtual environment every time you want to use the
``zhmc_prometheus_exporter`` command.

There are a number of ways how virtual Python environments can be created. This
documentation describes the use of "virtualenv".

1.  Prerequisite: Install the Python virtualenv package as an OS-level package
    or into the system Python.

    Follow the steps at https://virtualenv.pypa.io/en/latest/installation.html
    to install virtualenv.

2.  Create and activate a virtual Python environment:

    .. code-block:: bash

        $ virtualenv ~/.virtualenvs/zhmcpe
        $ source ~/.virtualenvs/zhmcpe/bin/activate

3.  Install the exporter into the virtual Python environment:

    To install the latest released version of the exporter so that it uses your
    default Python version:

    .. code-block:: bash

        (zhmcpe) $ pip install zhmc-prometheus-exporter

    To install a specific released version of the exporter, e.g. 1.7.1:

    .. code-block:: bash

        (zhmcpe) $ pip install zhmc-prometheus-exporter==1.7.1

    To install a specific development branch of the exporter, e.g. master:

    .. code-block:: bash

        (zhmcpe) $ pip install git+https://github.com/zhmcclient/zhmc-prometheus-exporter.git@master


Installation into a system Python
---------------------------------

Your system Python version(s) are installed using OS-level packages for all the
Python functionality.

Adding packages to your system Python using Python packages from `Pypi`_ may
create issues. This is why recent versions of pip raise a warning when
attempting to install into the system Python. Even if you install a Python
package from Pypi into your user's space, this may create issues.

The main issue is that the more Python packages you install into the system
Python, the more likely there will be incompatible Python package dependencies.

Another issue is when you replace OS-level packages with Python packages.

In order to avoid these issues, you should install the exporter into the system
Python only in cases where the system has a well-defined scope and you have
full control over the set of OS-level and Python-level packages, for example
when building a Docker container.


Installation on a system without Internet access
------------------------------------------------

When installing Python packages using pip or pipx, Internet access is needed to
access the Pypi repository.

If you want to install the exporter on a system that does not have Internet
access, you can do this by downloading the zhmc-prometheus-exporter package on
a download system that does have Internet access. This also downloads any
dependent Python packages. Then, these packages are made available to the target
system. e.g. via a shared file system or by transferring the files, and then you
can install the exporter from these files on the target system.

Important: The downloaded package files need to be compatible with the OS/HW
platform, Python version and Python implementation that will be used on the
target system. Pip by default uses the current Python and OS/HW platform to
determine these parameters. If the OS/HW platform, Python version or Python
implementation on the download system are not compatible with the target system,
you can use the pip options ``--platform``, ``--python-version`` and
``--implementation`` to select parameters that are compatible with the target
system.

For simplicity, the following example uses a shared file system between the
download and target systems, and has OS/HW platform, Python version and Python
implementation that are compatible between download system and target system.

On the download system:

.. code-block:: bash

    [download]$ python -c "import platform; print(platform.platform())"
    macOS-14.7.2-arm64-arm-64bit

    [download]$ python -c "import platform; print(platform.python_version())"
    3.13.0

    [download]$ python -c "import platform; print(platform.python_implementation())"
    CPython

    [download]$ mkdir download; cd download

    [download]$ python -m pip download zhmc-prometheus-exporter setuptools

    [download]$ ls -1
    MarkupSafe-3.0.2-cp313-cp313-macosx_11_0_arm64.whl
    . . . (more packages)
    setuptools-80.7.1-py3-none-any.whl
    . . . (more packages)
    zhmc_prometheus_exporter-2.0.1-py3-none-any.whl
    zhmcclient-1.21.0-py3-none-any.whl

On the target system, with an active virtual Python environment:

.. code-block:: bash

    [target](zhmcpe)$ python -c "import platform; print(platform.platform())"
    macOS-13.6.3-arm64-arm-64bit

    [target](zhmcpe)$ python -c "import platform; print(platform.python_version())"
    3.13.1

    [target](zhmcpe)$ python -c "import platform; print(platform.python_implementation())"
    CPython

    [target](zhmcpe)$ ls -1
    MarkupSafe-3.0.2-cp313-cp313-macosx_11_0_arm64.whl
    . . . (more packages)
    setuptools-80.7.1-py3-none-any.whl
    . . . (more packages)
    zhmc_prometheus_exporter-2.0.1-py3-none-any.whl
    zhmcclient-1.21.0-py3-none-any.whl

    [target](zhmcpe)$ python -m pip install -f . --no-index zhmc_prometheus_exporter-2.0.1-py3-none-any.whl

Note: Installation using pipx does not seem to work from a downloaded package
file.


Setting up the HMC
------------------

Usage of this package requires that the HMC in question is prepared
accordingly:

* The Web Services API must be enabled on the HMC.

  You can do that in the HMC GUI by selecting "HMC Management" in the left pane,
  then opening the "Configure API Settings" icon on the pain pane,
  then selecting the "Web Services" tab on the page that comes up, and
  finally enabling the Web Services API on that page.

  The above is on a z16 HMC, it may be different on older HMCs.

  If you cannot find this icon, then your userid does not have permission
  for the respective task on the HMC. In that case, there should be some
  other HMC admin you can go to to get the Web Services API enabled.

* The HMC should be configured to use a CA-verifiable certificate. This can be
  done in the HMC task "Certificate Management". See also the :term:`HMC Security`
  book and Chapter 3 "Invoking API operations" in the :term:`HMC API` book.

  For more information, see the
  `Security <https://python-zhmcclient.readthedocs.io/en/stable/security.html>`_
  section in the documentation of the 'zhmcclient' package.

  See :ref:`Using HMC certificates` for how to use HMC certificates with the
  zhmc command.

* The HMC userid that is used by the exporter must have the following flag
  enabled:

  - "Allow access to Web Services management interfaces" flag of the user in
    the HMC GUI, or "allow-management-interfaces" property of the user at the
    WS-API.

* The HMC userid that is used by the exporter must have object access permission
  to the objects for which metrics should be returned.

  If the userid does not have object access permission to a particular object,
  the exporter will behave as if the object did not exist, i.e. it will
  successfully return metrics for objects with access permission, and ignore
  any others.

  However, the parent objects of accessible objects of enabled metric groups
  also must be accessible for the user. This boils down to access permissions
  for the parent CPC, when metric groups for LPARs, partitions or adapters
  are enabled for export.

  The exporter can return metrics for the following types of objects. To
  return metrics for all existing objects, the userid must have object access
  permission to all of the following objects:

  - CPCs

  - On CPCs in DPM mode:

    - Adapters
    - Partitions
    - NICs

  - On CPCs in classic mode:

    - LPARs

* The HMC userid that is used by the exporter must have task permission for the
  "Manage Secure Execution Keys" task.

  This is used by the exporter during the 'Get CPC Properties' operation, but
  it does not utilize the CPC properties returned that way (room for future
  optimization).


Setting up firewalls or proxies
-------------------------------

If you have to configure firewalls or proxies between the system where you
run the ``zhmc_prometheus_exporter`` command and the HMC, the following ports
need to be opened:

* 6794 (TCP) - for the HMC API HTTP server
* 61612 (TCP) - for the HMC API message broker via JMS over STOMP

For details, see sections "Connecting to the API HTTP server" and
"Connecting to the API message broker" in the :term:`HMC API` book.
