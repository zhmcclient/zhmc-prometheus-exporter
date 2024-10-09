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


Change log
----------

.. ============================================================================
..
.. Do not add change records here directly, but create fragment files instead!
..
.. ============================================================================

.. towncrier start
Version 2.0.0
^^^^^^^^^^^^^

Released: 2024-10-09

**Incompatible changes:**

* Removed the '-m' option for specifying a metric definition file. The metric
  definition file is now part of the Python distribution archive and there
  is no need anymore for users to edit it. (`#418 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/418>`_)

* Changed the format of the exporter config file (previously referred to as
  "HMC credentials file") to add controls for enabling or disabling the export
  of the metric groups, and to clean up some naming idiosyncrasies on that
  opportunity. The old config file format is still supported and is automatically
  upgraded internally (or the file itself, see the support for the
  '--upgrade-config' option). As part of that config file upgrade, all metric
  groups are enabled by default. If you had edited the metric definition file
  in exporter version 1.x to disable some metric groups, you need to do that
  again in the upgraded exporter config file. (`#418 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/418>`_)

* Dropped support for Python 3.6 and 3.7. The minimum Python version is now 3.8. (`#570 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/570>`_)

* Changed the name of the Docker container image for the exporter from
  'zhmcexporter' to 'zhmc_prometheus_exporter' to match the command name. (`#633 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/633>`_)

**Bug fixes:**

* Addressed safety issues up to 2024-08-18.

* Test: Fixed coverage reporting (locally and on coveralls.io).

* Dev: Fixed several dependencies in Makefile.

* Dev: Fixed step that creates the release start tag when starting a new version.

* Test: Fixed the issue that coveralls was not found in the test workflow on MacOS
  with Python 3.9-3.11, by running it without login shell. Added Python 3.11 on
  MacOS to the normal tests.

* Dev: Fixed new issue 'too-many-positional-arguments' reported by Pylint 3.3.0.

* Fixed a bug where resources that ceased their existence while the exporter
  was running were removed from the internal data structures such that in some
  cases the wrong resource was removed from the internal data structures,
  either leading to an immediate IndexError, or to follow-on errors lateron. (`#609 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/609>`_)

* Fixed the build of the docker image which failed with an ImportError
  on the rpds package. Added test for running the docker image. (`#623 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/623>`_)

* Test: Added new indirect dependencies for package installation to the
  minimum-constraints.txt file to make sure the package is tested with defined
  minimum versions. (`#623 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/623>`_)

* Increased minimum version of zhmcclient to 1.18.0 to pick up fixes. (`#635 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/635>`_)

* Fixed incorrect check for start branch in 'make start_tag'. (`#638 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/638>`_)

* Fixed incorrect check for release branch in 'make release_publish'.

**Enhancements:**

* Improved build of the Docker image: It now uses the package version as the
  image tag, sets OCI metadata as labels, and reduces the image size by using
  the python:3.12-alpine base image, building from the Python distribution
  archive instead of copying the repo, uninstalling pip, setuptools and
  wheel since they are not needed to run the exporter, and using a multi-staged
  build to copy just the installed Python packages. This reduced the image file
  size with Docker on Ubuntu from 256 MB to 73 MB.

* Support for and test of Python 3.13.0-rc.1. Needed to increase the minimum
  versions of PyYAML to 6.0.2 and pyrsistent to 0.20.0. (`#517 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/517>`_)

* Dev: Migrated from setup.py to pyproject.toml with setuptools as build backend.
  This provides for automatic determination of the package version without
  having to edit a version file. (`#520 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/520>`_)

* Added support for running the 'ruff' checker via "make ruff" and added that
  to the test workflow. (`#522 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/522>`_)

* Added support for running the 'bandit' checker with a new make target
  'bandit', and added that to the GitHub Actions test workflow.
  Adjusted the code in order to pass the bandit check. (`#523 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/523>`_)

* Test: Added tests for Python 3.13 (final version). (`#525 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/525>`_)

* Support for upgrading a config file (= HMC credentials file) from exporter
  version 1.x to the current version. By default, the exporter configuration is
  upgraded internally without persisting the changes. A new '--upgrade-config'
  command line option can be used to upgrade the exporter config file. This
  required using the 'ruamel.yaml' Python package, in order to preserve comments
  in the exporter config file. (`#571 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/571>`_)

* Dev: Encapsulated the starting of a new version into new 'start_branch' and
  'start_tag' make targets. See the development documentation for details. (`#617 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/617>`_)

* Dev: Encapsulated the releasing of a version to PyPI into new 'release_branch'
  and 'release_publish' make targets. See the development documentation for
  details. (`#617 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/617>`_)

**Cleanup:**

* Dev: Relaxed the conditions when safety issues are tolerated:
  Issues in development dependencies are now tolerated in normal and scheduled
  test workflow runs (but not in local make runs and release test workflow runs).
  Issues in installation dependencies are now tolerated in normal test workflow
  runs (but not in local make runs and scheduled/release test workflow runs).

* Dev: Added to the release instructions to roll back fixes for safety issues
  into any maintained stable branches.

* Dev: Added to the release instructions to check and fix dependabot issues,
  and to roll back any fixes into any maintained stable branches.

* Dev: Removed dependency to unmaintained py package.

* Dev: Removed ignore entries in safety profiles that meanwhile became
  unnecessary due to increasing versions.

* Dev: Started using the trusted publisher concept of Pypi in order to avoid
  dealing with Pypi access tokens.

* Because the metrics file is now part of the package, adjusted any error messages
  dealing with the metrics file accordingly. (`#577 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/577>`_)

* Dev: Dropped the 'make upload' target, because the release to PyPI has
  been migrated to using a publish workflow. (`#617 <https://github.com/zhmcclient/zhmc-prometheus-exporter/issues/617>`_)


Version 1.7.0
^^^^^^^^^^^^^

This version contains all fixes up to version 1.6.1.

Released: 2024-08-01

**Bug fixes:**

* Fixed a bug in the metric definition file that lead to
  HTTP error 400,14 "'absolute-ifl-capping'' is not a valid value for the
  corresponding query parm". Please download the fixed metric definition file
  from the repo. (issue #564)

* Addressed safety issues up to 2024-07-21.

* In the Github Actions test workflow for Python 3.6 and 3.7, changed
  macos-latest back to macos-12 because macos-latest got upgraded from macOS 12
  to macOS 14 which no longer supports these Python versions.

* Docs: Fixed README badges by converting it to Markdown. (issue #507)

* Dev: Added missing development requirement for 'filelock' package.

* Fixed AttributeError when using 'storage_groups' on 'Client' object.

* Vendorized a forked version 0.20.0.post1 of the 'prometheus_client' package
  to pick up the following fixes:

  - Fixed HTTP verb tampering test failures. (issue #494)
  - Fixed vulnerabilities in Prometheus server detected by testssl.sh.
    (issues #508, #509)

* Fixed AttributeError when adding NICs after intial startup.

**Enhancements:**

* Docs: Added a section about the size of captured terminal output and log
  files. (issue #528)

* Docs: Improved the section about HMC certificates. (related to issue #529)

* Added the original line where the exception occurred to any messages that
  display exceptions, for easier problem determination.

**Cleanup:**

* Removed lengthy display of URI to resource cache when ignoring labels due to
  Jinja2 error.

* Dev: Removed support for editable installs, because pip 25 will disable that.
  (issue #546)

* Minimized symbols when importing zhmc_prometheus_exporter.

* Improved messages where metrics, metric groups or labels are ignored due to
  some issue, for better clarity. (related to issue #539)


Version 1.6.0
^^^^^^^^^^^^^

This version contains all fixes up to version 1.5.2.

Released: 2024-04-03

**Important:** The standard metric definitions file examples/metrics.yaml has
been updated. Please use the new file in your setup. This new exporter version
will also work with the prior version of the file (but not vice versa).

**Bug fixes:**

* Addressed safety issues up to 2024-02-18.

* Docs: Increased minimum Sphinx versions to 7.1.0 on Python 3.8 and to 7.2.0 on
  Python >=3.9 and adjusted dependent package versions in order to fix a version
  incompatibility between sphinxcontrib-applehelp and Sphinx.
  Disabled Sphinx runs on Python <=3.7 in order to no longer having to deal
  with older Sphinx versions. (issue #444)

* Docs: Added missing 'se_version' variable to description of 'export-condition'
  and 'fetch-condition' in the Usage section. (part of issue #459)

* Fixed warning about ignoring label 'adapter/port' on metric group
  'partition-attached-network-interface' due to error in rendering the Jinja2
  expression for a label value. (issue #450)

* Added missing fetch-conditions to all remaining properties of resource metric
  groups that were added at some point in the HMC/SE, but so far were assumed
  to always be present.

* Docs: Added missing metrics to the metrics table in the Usage section:
  zhmc_partition_storage_group_uris

* Dev: Fixed the call to pipdeptree in the test workflow to use 'python -m'
  because otherwise it does not show the correct packages of the virtual env.

* Fixed traceback when HMC credentials file does not exist.

* Fixed the name of the 'power-consumption-watts' metric in the
  'logical-partition-usage' HMC metric group. (issue #475)

* Fixed that the 'number-{cpu}-processors' and 'number-reserved-{cpu}-processors'
  properties of LPARs were retrieved for all HMC/SE versions, but they were
  introduced only with SE/CPC version 2.15.0. (issue #474)

* Docs: Fixed link in description how to verify release in development.rst.

* Added description of missing verify_cert parameter to help text for HMC
  credentials file, displayed with --help-creds.

**Enhancements:**

* Increased zhmcclient version to 1.14.0 to pick up fixes and improvements.

* Split safety runs into one against all requirements that may fail and one
  against the install requirements that must succeed. (issue #441)

* Changed safety run for install dependencies to use the exact minimum versions
  of the dependent packages, by moving them into a separate
  minimum-constraints-install.txt file that is included by the existing
  minimum-constraints.txt file. (issue #489)

* Added support for the following new variables for use in 'fetch-condition' in
  the metric definition file (issue #459):

  - 'hmc_api_version' - HMC API version as a tuple of integers (M, N)
  - 'hmc_features' - List of names of HMC API features

* Added support for the following new variables for use in 'export-condition'
  in the metric definition file (issue #459):

  - 'hmc_api_version' - HMC API version as a tuple of integers (M, N)
  - 'hmc_features' - List of names of HMC API features
  - 'se_features' - List of names of SE/CPC API features
  - 'resource_obj' - zhmcclient resource object for the metric

* Used these new variables to improve the conditions in the metric definition
  file in order to eliminate the following warnings about properties not
  returned by the HMC (issue #459):

  - 'cylinders' in resource metric group 'storagevolume-resource'
    (only returned for FC-type storage groups)
  - 'max-partitions' in resource metric group 'storagegroup-resource'
    (only returned for FCP-type storage groups)
  - Various cbp related properties in resource metric groups 'cpc-resource'
    and 'logical-partition-resource' (only returned for SE versions between
    2.14.0+MCLs and 2.15.0)

* Added support for environment variables 'TESTCASES' for specifying testcases
  for the unit test, and 'TESTOPTS' for specifying pytest options. (issue #461)

* Added support for the new partition power consumption metrics in z16
  (issue #448):

  In metric group 'zcpc-environmentals-and-power':

  - 'zhmc_cpc_total_partition_power_watt' - Total power consumption of all
    partitions of the CPC
  - 'zhmc_cpc_total_infrastructure_power_watt' - Total power consumption of all
    infrastructure components of the CPC
  - 'zhmc_cpc_total_unassigned_power_watt' - Total power consumption of all
    unassigned components of the CPC

  In metric group 'logical-partition-usage':

  - 'zhmc_partition_power_watt' - Power consumption of the partition

* Added support for regularly fetching properties in the background, for which
  object change notifications are not supported. These properties are defined
  in the metric definition file along with an 'if' condition to express in
  which environment they need to be fetched. The properties are fetched in the
  background in a property fetch thread. The cycle time for fetching is
  initially 30 seconds and will be adjusted to the cycle time in which
  Prometheus fetches the exported metrics. (issue #358)

* Added support for a new make target 'authors' that generates an AUTHORS.md
  file from the git commit history. (issue #442)

* The safety run for all dependencies now must succeed when the test workflow
  is run for a release (i.e. branch name 'release\_...').

* When the HMC userid cannot log on to the HMC because the password is invalid
  or expired, or because the maximum number of sessions has been reached, the
  exporter no longer retries the logon but abandons. The previous retrying has
  lead to disabling the userid after some unsuccessful retries. (issue #493)

* Warning messages are now always printed to the output, and not just in verbose
  mode (related to issue #488).

* Added more detailed messages in the output and log for understanding the
  Jinja2 rendering issue reported in issue #488.

**Cleanup:**

* Increased versions of GitHub Actions plugins to increase node.js runtime
  to version 20.

* Disabled the use of Python builtins in the evaluation of 'fetch-condition' and
  'export-condition' in the metric definition file. (issue #463)

* Improved the lengthy warning details messages when resources have not been
  found to a more condensed and useful format. (issue #473)


Version 1.5.0
^^^^^^^^^^^^^

This version contains all fixes up to version 1.4.3.

Released: 2023-11-28

**Incompatible changes:**

* Installation of this package using "setup.py" is no longer supported.
  Use "pip" instead.

**Bug fixes:**

* Addressed safety issues up to 2023-11-26.

* Improved and fixed Dockerfile. (issue #297)

* Docs: Fixed incorrect label value syntax in the documentation. (issue #310)

* Fixed incorrect label 'phase' on the line cord metrics ('zhmc_cpc_power_cord\*').
  It was incorrectly shown as "None", and now has the correct values "A", "B",
  or "C".

* Fixed RTD docs build ssue with OpenSSL version by providing a .readthedocs.yaml
  file that specifies Ubuntu 22.04 as the build OS.

* Increased minimum zhmcclient version to 1.9.1 to pick up fixes and improvements
  for HMC session handling, including the handling of HTTP 403.4. (related to
  issue #336) and the version change for PyYAML in zhmcclient.

* Occurrences of most HTTP 403.x failures are now handled by logging on again
  and retrying, instead of abandoning. (related to issue #336)

* Improved robustness of evaluating Jinja2 label expressions by ignoring
  labels with expressions that fail, instead of stopping the exporter. A
  warning message is shown and a log record is written when that happens.

* Addressed safety issues from 6+7/2023, by increasing 'requests' to 2.31.0
  on Python >=3.7, and by increasing other packages only needed for development.

* Fixed issue with PyYAML 5.4 installation on Python>=3.10 that fails since
  the recent release of Cython 3.

* Test: Circumvented a pip-check-reqs issue by excluding its version 2.5.0.

* Added handling of exceptions raised by the built-in HTTP server during
  its startup, for the HTTP case. (related to issue #397)

* Docs: Added the missing requirement for having the HMC userid enabled for
  web services access. (issue #419)

* Fixed LPAR resource metrics '..._processor_count_is_capped' and
  '..._processor_cap' for absolute cappping.

* Fixed ruamel.yaml issue on Python 3.6 by pinning to <0.17.22

* Dev: Resolved dependency conflict with importlib-metadata on Python 3.7

**Enhancements:**

* Added support for Python 3.12. Had to increase the minimum versions of
  setuptools to 66.1.0 and pip to 23.1.2 in order to address removal of the
  long deprecated pkgutils.ImpImporter in Python 3.12, as well as several
  packages used only for development. (issue #388)

* Added a '--version' option for showing the versions of the exporter and
  the zhmcclient library. (issue #298)

* Enabled the 'partition-attached-network-interface' metric group in the
  standard/example metric definition file. It had been disabled for performance
  reasons, but with the auto-update support for resources, there is no
  visible performance impact anymore when Prometheus fetches the metrics.

* Test: Added a test script 'validate_adapter_metrics.py' for validating
  the adapter/NIC resources for which metrics are returned by the HMC.

* Added a troubleshooting section to the docs.

* Added zhmc_partition_description metric with partition / LPAR description in
  the 'value' label, for cases where the partition description contains further
  information that can be parsed. (issue #345)

* Added resource-based metrics for storage groups and storage volumes. Added
  a new metric zhmc_partition_storage_groups that lists the storage groups
  attached to a partition. (issue #346)

* Added support for HTTPS and mutual TLS (mTLS) by adding a new optional section
  'prometheus' to the HMC credentials file and using prometheus-client 0.19.0.
  (issue #347)

* Tolerated when unknown 'resource' types are specified in the metrics.yaml
  file, because one possible reason for that is that a newer metrics.yaml file
  is being used. (issue #379)

* Added adapter name and port index as two new labels 'adapter' and 'port' to
  metric group 'partition-attached-network-interface'. (issue #347)

* Added handling of evaluation errors for 'if' conditions in metric definition
  files.

**Cleanup:**

* Resource-based metrics defined in the metric definition file but not
  returned by the HMC as a resource property (e.g. because the HMC manages
  older SE versions) now cause a Python warning to be printed. Added the
  respective 'if' conditionals to the default metric definition file for such
  HMC or SE version dependent resource metrics.


Version 1.4.0
^^^^^^^^^^^^^

This version contains all fixes up to version 1.3.2.

Released: 2023-03-27

**Incompatible changes:**

* The label value definitions in the metric definition file are now interpreted
  as Jinja2 expressions and no longer with the special syntax used before.

  This is an incompatible change and requires updating the metric definition
  file accordingly. The example metric definition file provided with the package
  has been updated accordingly. If you have used the example file unchanged,
  you only need to use the new version of the file. If you have used your own
  version of the metric definition file, you need to update it. For
  understanding the changes and what to update, compare the old and new version
  of the example metric definition file.

* The extra label value definitions in the HMC credentials file are now
  interpreted as Jinja2 expressions and no longer as literals.

  This is an incompatible change and requires updating your HMC credentials file
  in case you used the 'extra_labels' property in there.
  The change to make is to put the literal label values into nested double and
  single quotes.

  Example old definition in the file::

      extra_labels:
        - name: hmc
          value: MYHMC1

  Corresponding new definition in the file::

      extra_labels:
        - name: hmc
          value: "'MYHMC1'"

* Changed the names of exported metrics with unit Watt from '\*_watts' to
  '\*_watt':

  - zhmc_cpc_power_watts -> zhmc_cpc_power_watt
  - zhmc_cpc_power_cord{C}_phase_{P}_watts -> zhmc_cpc_power_cord{C}_phase_{P}_watt

**Bug fixes:**

* Fixed that not using the `--log` option resulted in an error message
  about invalid use of the `--log-comp` option. (issue #234)

* Fixed an erroneous timezone offset in log timestamps. (issue #241)

* Fixed the log entry for version 1.3.0 that showed an incorrect new timestamp
  format.

* Fixed a flake8 AttributeError when using importlib-metadata 5.0.0 on
  Python >=3.7, by pinning importlib-metadata to <5.0.0 on these Python
  versions.

* Test: Fixed install error of Python 2.7, 3,5, 3,6 on Ubuntu in GitHub Actions.

* Fixed new issues of Pylint 2.16. Fixed versions of Pylint dependents and their
  Python versions.

* Added missing packages (pip_check_reqs, pipdeptree) to be checked for their
  dependencies in minimum-constraints.txt.

* Fixed CBP related metrics in classic mode CPCs in HMC 2.16. These metrics
  were removed in z16 but the metric definition file tried to export them,
  leading to a failure with z16 CPCs in classic mode. This was fixed by
  exporting these metrics only if the CPC has the SE version that supports them.

* Fixed the '\*_central_memory_mib' and '\*_expanded_memory_mib' metrics of
  LPARs of classic mode CPCs that caused the exporter to fail.

* Updated the minimum version of zhmcclient to 1.7.0 to pick up a fix for
  cases where a CPC resource is not found (may happen on older HMCs such as
  2.14). Changed error handling to tolerate that case.

**Enhancements:**

* Added support for labels on single metric definitions, for defining how the
  Prometheus metric value should be interpreted. A `value` lebel can define
  a string-typed property value that should be used instead. This has been
  used to show the original staus values, e.g. as `value="operating"`.
  A `valuetype` label can define that the floating point value of the
  Prometheus metric should be interpreted as a boolean or integer value. This
  has been used for any boolean metrics. (issue #224)

* Simplified release process by adding a new GitHub Actions workflow publish.yml
  to build and publish to PyPI

* Added exporter and zhmcclient version and verbosity level to log.

* When enabling auto-update for a resource fails, the exporter will now record
  an error log message that the resource is ignored, but will otherwise
  continue with its operation. Previously, it terminated in such a case.

* Docs: Added sections on HMC setup and setup of firewalls and proxies that
  may be between you and the HMC. (issues #260 and #261)

* Added missing environments to weekly full tests (Python 3.5,3.6 on Windows
  and MacOS).

* Added some critical environments to normal PR tests (Python 3.10/min on
  Windows).

* Changed to using the 'build' package for building the distribution archives
  instead of 'setup.py' commands, following the recommendation of the Python
  packaging community
  (see https://blog.ganssle.io/articles/2021/10/setup-py-deprecated.html).

* The label value definitions in the metric definition file are now interpreted
  as Jinja2 expressions and no longer with the special keyword syntax used
  before. This is an incompatible change for the metric definition file, see the
  corresponding item in the incompatible changes section of this change log.
  The example metric definition file provided with the package has been updated
  accordingly.

* The extra label value definitions in the HMC credentials file are now
  interpreted as Jinja2 expressions and no longer as just literals. This is an
  incompatible change for the HMC credentials file, see the corresponding
  item in the incompatible changes section of this change log.
  The example HMC credentials file provided with the package has been updated
  accordingly.

* Added support for conditional exporting of single metrics based on the
  HMC and SE/CPC version, by adding an 'if' property to the metric definition in
  the metric definition file that can specify a Python expression using
  the 'hmc_version' and 'se_version' variables. Used that capability on CBP
  related metrics that were added in z14 and removed in z16 to specify the
  supported SE version range.

* Made handling of runtime errors more tolerant for properties that are
  not present in certain cases.

* Docs: Added a link to the description of Jinja2 expressions.

* Added labels to all 'zhmc_cpc_power_cord\*' metrics:

  - 'cord' - line cord name (as reported in metric 'linecord-eight-name')
  - 'cordid' - line cord ID (1, 2, ..., 8)
  - 'phase' - line cord phase (A, B, C)

* Added support for Python 3.11.

* Improved and shortened the error message for validation errors in the
  metric definition file and HMC credentials file. As part of that, increased
  the minimum version of the jsonschema package to 3.2.0 and of the pyrsistent
  package to 0.17.3 on Python<=3.6 and 0.18.1 on Python>=3.7.

* Added a check for consistency of items in metrics and metric_groups in
  the metric definition file.

**Cleanup:**

* Addressed issues in test workflow reported by Github Actions. (issue #264)

* Increased minimum versions of pip, setuptools, wheel to more recent versions.

* Changed the names of exported metrics with unit Watt from '\*_watts' to
  '\*_watt', for consistency:

  - zhmc_cpc_power_watts -> zhmc_cpc_power_watt
  - zhmc_cpc_power_cord{C}_phase_{P}_watts -> zhmc_cpc_power_cord{C}_phase_{P}_watt


Version 1.3.0
^^^^^^^^^^^^^

Released: 2022-09-05

**Incompatible changes:**

* The log format has changed from:
  "2022-08-17 09:24:41,037 logger: message"
  to:
  "2022-08-17 07:24:41+0000 LEVEL logger: message"

**Bug fixes:**

* Fixed that HMC exceptions were not caught during cleaning when exiting.

* Docs: Fixed that the "Logging" section in the documentation described the
  '--log' option as '--log-dest'.

**Enhancements:**

* HMC resources that no longer exist are automatically removed from the
  exported metrics. (Issue #203)

* Increased minimum version of zhmcclient to 1.4.0 to pick up fixes and
  required new functions. (issue #220)

* Extended the existing --log-comp option to allow specifying a log level for
  each component with COMP=LEVEL, and to add support for a component 'all'
  that affects all components.

* Optimized the log levels of many log messages and the verbosity level of some
  output messages.

* Added cleanup log and output messages when exiting.

* Added support for logging to the System Log (syslog). (issue #219)


Version 1.2.0
^^^^^^^^^^^^^

Released: 2022-06-26

**Incompatible changes:**

* For classic mode CPCs, changed the name of the LPAR status metric from
  `zhmc_partition_status_int` to `zhmc_partition_lpar_status_int` in order to
  disambiguate it from the same-named metric for partitions on CPCs in DPM
  mode. (issue #207)

**Bug fixes:**

* Fixed Pylint config file because pylint 2.14 rejects older options
  (issue #202)

* The read timeout for HMC interactions was increased from 120 sec to 300 sec.
  The retry count remains at 2. (issue #210)

**Enhancements:**

* Increased the minimum version of zhmcclient to 1.3.1, in order to have
  the exported JMS logger name symbol. (part of issue #209)

* Added support for logging HMC notifications with new "jms" log component.
  (issue #209)


Version 1.1.0
^^^^^^^^^^^^^

This version contains all fixes up to version 1.0.0.

Released: 2022-04-07

**Bug fixes:**

* Fixed new issues reported by Pylint 2.10.

* Disabled new Pylint issue 'consider-using-f-string', since f-strings were
  introduced only in Python 3.6.

* The hmccreds_schema.yml schema incorrectly specified the items of an array
  as a list. That was tolerated by JSON schema draft 07. When jsonschema 4.0
  added support for newer JSON schema versions, that broke. Fixed that by
  changing the array items from a list to its list item object. Also,
  in order to not fall into future JSON schema incompatibilities again, added
  $schema: http://json-schema.org/draft-07/schema (issue #180)

* Increased minimum zhmcclient version to 1.2.0 to pick up the automatic
  presence of metric group definitions in its mock support, and adjusted
  testcases accordingly. This accomodates the removal of certain metrics
  related mock functions in zhmcclient 1.2.0 (issue #194)

* Made the cleanup when stopping the exporter program more tolerant against
  meanwhile closed HMC sessions or removed metrics contexts, eliminating
  exceptions that were previously shown when interrupting the exporter
  program. (related to issue #193)

* Fixed an AttributeError exception when retrying the metrics collection after
  the HMC was rebooted. (related to issue #193)

**Enhancements:**

* Changed the "Exporter is up and running" message to be shown also in
  non-verbose mode to give first-time users a better feedback on when it is
  ready.

* Support for Python 3.10: Added Python 3.10 in GitHub Actions tests, and in
  package metadata.

* Docs: Documented the authorization requirements for the HMC userid.
  (issue #179)

* Improved the information in authentication related error messages to
  better distinguish between client (=setup) errors and HMC authentication
  errors, and to include the HTTP reason code in the latter case.
  (related to issue #193)

* Showed some more messages in verbose mode for re-creating the HMS session
  and re-creating the metrics context in case the HMC has rebooted.
  (related to issue #193)

**Cleanup:**

* Removed an unnecessary recreation of the HMC session when re-creating
  the metrics context on the HMC. (related to issue #193)

* Changed debug messages when metric value resource was not found on HMC, to
  messages that are output and logged.


Version 1.0.0
^^^^^^^^^^^^^

Released: 2021-08-08

**Incompatible changes:**

* Dropped support for Python 3.4. (issue #155)

* Changed some network metrics to be represented using Prometheus counter metric
  types. Specifically, the following metrics at the NIC and port level have been
  changed to counters: (issue #160)

  - bytes_sent_count
  - bytes_received_count
  - packets_sent_count
  - packets_received_count
  - packets_sent_dropped_count
  - packets_received_dropped_count
  - packets_sent_discarded_count
  - packets_received_discarded_count
  - multicast_packets_sent_count
  - multicast_packets_received_count
  - broadcast_packets_sent_count
  - broadcast_packets_received_count

**Bug fixes:**

* Fixed new isues reported by Pylint 2.9.

**Enhancements:**

* Added support for metrics based on resource properties of CPCs, partitions
  (DPM mode) and LPARs (classic mode). (issue #112)

* Added support for metrics representing CPC and partition status. (issue #131)

* Increased minimum version of zhmcclient to 1.0.0 to pick up support for
  auto-updated resources. (issue #156)

* Added support for testing with minimum package levels. (issue #59)

* Added a new make target 'check_reqs' for checking dependencies declared in
  the requirements files.

* Increased minimum versions of dependent packages to address install issues
  on Windows and with minimum package levels:
  - prometheus-client from 0.3.1 to 0.9.0
  - jinja2 from 2.0.0 to 2.8


Version 0.7.0
^^^^^^^^^^^^^

Released: 2021-06-15

This version contains all fixes up to version 0.6.1.

**Incompatible changes:**

* The zhmc_prometheus_exporter command now verifies HMC server certificates by
  default, using the CA certificates in the 'certifi' Python package. This
  verification will reject the self-signed certificates the HMC is set up with
  initially. To deal with this, install a CA-verifiable certificate in the HMC
  and specify the correct CA certificates with the new 'verify_cert' attribute
  in the HMC credentials file.
  As a temporary quick fix or in non-production environments, you can also
  disable the verification with that new attribute.

**Bug fixes:**

* Mitigated the coveralls HTTP status 422 by pinning coveralls-python to
  <3.0.0.

**Enhancements:**

* Increased minimum version of zhmcclient to 0.31.0, mainly driven by its
  support for verifying HMC certificates.

* Added support for logging the HMC interactions with new options `--log-dest`
  and `--log-comp`. (issue #121)

* Added the processor type as a label on the metrics of the 'zcpc-processor-usage'
  metrics group. (issue #102)

* Docs: Added sample Prometheus output from the exporter.

* Improved error handling and recovery. Once the exporter is up and running,
  any connectivity loss is now recovered by retrying eternally.

* Added exporter level activities to the log, as a new log component "exporter".
  All messages that would be displayed at the highest verbosity level are now
  also logged, regardless of the actual verbosity level.
  Changed the log format by removing the level name and adding the timestamp.

* Changed the retry/timeout configuration used for the zhmcclient session,
  lowering the retry and timeout parameters for connection and reads. This
  only affects how quickly the exporter reacts to connectivity issues, it does
  not lower the allowable response time of the HMC.

* The zhmc_prometheus_exporter command now supports verification of the HMC
  server certificate. There is a new configuration attributes in the HMC
  credentials file ('verify_cert') that controls the verification behavior.


Version 0.6.0
^^^^^^^^^^^^^

Released: 2020-12-07

**Bug fixes:**

* Docs: Fixed the names of the Prometheus metrics of the line cord power metrics.
  (see issue #89)

* Added missing dependency to 'urllib3' Python package.

* README: Fixed the links to the metric definition and HMC credentials files
  (see issue #88).

* Dockerfile: Fixed that all files from the package are included in the Docker
  image (see issue #91).

**Enhancements:**

* Added support for specifying a new optional property `if` in the definition of
  metric groups in the metric definition file, which specifies a Python
  expression representing a condition under which the metric group is fetched.
  The HMC version can be specified in the expression as a `hmc_version` variable.
  (see issue #77)

**Cleanup:**

* The metric definition and HMC credentials YAML files are now validated using
  a schema definition (using JSON schema). This improved the ability to
  enhance these files, and allowed to get rid of error-prone manual validation
  code. The schema validation files are part of the installed Python package.
  This adds a dependency to the 'jsonschema' package. (see issue #81)


Version 0.5.0
^^^^^^^^^^^^^

Released: 2020-12-03

**Incompatible changes:**

* The sample metric definition file has changed the metric names that are
  exported, and also the labels. This is only a change if you choose to
  use the new sample metric definition file; if you continue using your
  current metric definition file, the exported metrics will be as before.

**Enhancements:**

* The packages needed for installation are now properly reflected
  in the package metadata (part of issue #55).

* Improved the metric labels published along with metric values in multiple
  ways. The sample metric definition file has been updated to exploit all
  these new capabilities:

  - The type of resource to which a metric value belongs is now identified in
    the label name e.g. by showing a label 'cpc' or 'adapter' instead of the
    generic label 'resource'.

  - Resources that are inside a CPC (e.g. adapters, partitions) now can show
    their parent resource (the CPC) as an additional label, if the metric
    definition file specifies that.

  - Metrics that identify the resource (e.g. 'channel-id' in the 'channel-usage'
    metric group now can used as additional labels on the actual metric value,
    if the metric definition file specifies that.

  Note that these changes will only become active if you pick them up in your
  metric definition file, e.g. by using the updated sample metric definition
  file. If you continue to use your current metric definition file, nothing will
  change regarding the labels.

* The published metrics no longer contain empty HELP/TYPE comments.

* Metrics with the special value -1 that are returned by the HMC for some
  metrics in case the resource does not exist, are now suppressed.

* Disabled the Platform and Python specific additional metrics so that they
  are not collected or published (see issue #66).

* Overhauled the complete documentation (triggered by issue #57).

* Added a cache for looking up HMC resources from their resource URIs to
  avoid repeated lookup on the HMC. This speeds up large metric retrievals
  from over a minute to sub-seconds (see issue #73).

* Added a command line option `-v` / `--verbose` to show additional verbose
  messages (see issue #54).

* Showing the HMC API version as a verbose message.

* Removed ensemble/zBX related metrics from the sample metric definition file.

* Added all missing metrics up to z15 to the sample metric definition file.

* Added support for additional labels to be shown in every metric that is
  exported, by specifying them in a new `extra_labels` section of the HMC
  credentials file. This allows providing some identification of the HMC
  environment, if needed. (see issue #80)

**Cleanup:**

* Removed the use of 'pbr' to simplify installation and development
  (see issue #55).


Version 0.4.1
^^^^^^^^^^^^^

Released: 2020-11-29

**Bug fixes:**

* Fixed the error that only a subset of the possible exceptions were handled
  that can be raised by the zhmcclient package (i.e. only ConnectionTimeout
  and ServerAuthError). This lead to lengthy and confusing tracebacks being
  shown when they occurred. Now, they are all handled and result in a proper
  error message.

* Added metadata to the Pypi package declaring a development status of 4 - Beta,
  and requiring the supported Python versions (3.4 and higher).

**Enhancements:**

* Migrated from Travis and Appveyor to GitHub Actions. This required several
  changes in package dependencies for development.

* Added options `--help-creds` and `--help-metrics` that show brief help for
  the HMC credentials file and for the metric definition file, respectively.

* Improved all exception and warning messages to be better understandable
  and to provide the context for any issues with content in the HMC credentials
  or metric definition files.

* Expanded the supported Python versions to 3.4 and higher.

* Expanded the supported operating systems to Linux, macOS, Windows.

* Added the sample HMC credentials file and the sample metric definition file
  to the appendix of the documentation.

* The sample metric definition file 'examples/metrics.yaml' has been completed
  so that it now defines all metrics of all metric groups supported by
  HMC 2.15 (z15). Note that some metric values have been renamed for clarity
  and consistency.


Version 0.4.0
^^^^^^^^^^^^^

Released: 2019-08-21

**Bug fixes:**

- Avoid exception in case of a connection drop error handling.

- Replace yaml.load() by yaml.safe_load(). In PyYAML before 5.1,
  the yaml.load() API could execute arbitrary code if used with untrusted data
  (CVE-2017-18342).


Version 0.3.0
^^^^^^^^^^^^^

Released: 2019-08-11

**Bug fixes:**

- Reconnect in case of a connection drop.


Version 0.2.0
^^^^^^^^^^^^^

Released: 2018-08-24

**Incompatible changes:**

- All metrics now have a ``zhmc_`` prefix.

**Bug fixes:**

- Uses Grafana 5.2.2.


Version 0.1.2
^^^^^^^^^^^^^

Released: 2018-08-23

**Enhancements:**

- The description now instructs the user to ``pip3 install zhmc-prometheus-exporter``
  instead of running a local install from the cloned repository. It also links
  to the stable version of the documentation rather than to the latest build.


Version 0.1.1
^^^^^^^^^^^^^

Released: 2018-08-23

Initial PyPI release (0.1.0 was for testing purposes)


Version 0.1.0
^^^^^^^^^^^^^

Released: Only on GitHub, never on PyPI

Initial release
