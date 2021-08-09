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


Version 1.0.0.dev1
^^^^^^^^^^^^^^^^^^

This version contains all fixes up to version 0.7.x.

Released: not yet

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

**Deprecations:**

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

**Cleanup:**

**Known issues:**

* See `list of open issues`_.

.. _`list of open issues`: https://github.com/zhmcclient/zhmc-prometheus-exporter/issues


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
