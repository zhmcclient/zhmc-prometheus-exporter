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
