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


Version 1.5.0.dev1
^^^^^^^^^^^^^^^^^^

This version contains all fixes up to version 1.4.x.

Released: not yet

**Incompatible changes:**

**Deprecations:**

**Bug fixes:**

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

* Fixed safety issues from 2023-08-27.

* Test: Circumvented a pip-check-reqs issue by excluding its version 2.5.0.

**Enhancements:**

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

**Cleanup:**

**Known issues:**

* See `list of open issues`_.

.. _`list of open issues`: https://github.com/zhmcclient/zhmc-prometheus-exporter/issues


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
