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

.. Include all that apply in your change log message
.. **Incompatible changes**
.. **Deprecations**
.. **Bug fixes**
.. **Enhancements**
.. **Known issues**

Change log
----------

Version 0.3.0
^^^^^^^^^^^^^

Released: 2019-08-11

**Bug fixes:**
- Reconnect in case of a connection drop.

**Known issues:** See the `list of open issues`_.

.. _list of open issues: https://github.com/zhmcclient/zhmc-prometheus-exporter/issue


Version 0.2.0
^^^^^^^^^^^^^

Released: 2018-08-24

**Incompatible changes:** All metrics now have a ``zhmc_`` prefix.

**Bug fixes:** Uses Grafana 5.2.2.

**Known issues:** See the `list of open issues`_.

.. _list of open issues: https://github.com/zhmcclient/zhmc-prometheus-exporter/issues


Version 0.1.2
^^^^^^^^^^^^^

Released: 2018-08-23

**Enhancements:** The description now instructs the user to ``pip3 install zhmc-prometheus-exporter`` instead of running a local install from the cloned repository. It also links to the stable version of the documentation rather than to the latest build.

Version 0.1.1
^^^^^^^^^^^^^

Released: 2018-08-23

Initial PyPI release (0.1.0 was for testing purposes)

Version 0.1.0
^^^^^^^^^^^^^

Released: Only on GitHub, never on PyPI

Initial release
