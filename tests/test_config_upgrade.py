# Copyright 2024 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the config file upgrade support"""

import sys
import re
import tempfile
import pytest

from zhmc_prometheus_exporter import zhmc_prometheus_exporter


# Default metric groups that are added to a version 1 config file
# pylint: disable=R0801
DEFAULT_METRIC_GROUPS = """metric_groups:
  cpc-usage-overview:
    export: true
  logical-partition-usage:
    export: true
  channel-usage:
    export: true
  crypto-usage:
    export: true
  flash-memory-usage:
    export: true
  roce-usage:
    export: true
  logical-partition-resource:
    export: true
  dpm-system-usage-overview:
    export: true
  partition-usage:
    export: true
  adapter-usage:
    export: true
  network-physical-adapter-port:
    export: true
  partition-attached-network-interface:
    export: true
  partition-resource:
    export: true
  storagegroup-resource:
    export: true
  storagevolume-resource:
    export: true
  zcpc-environmentals-and-power:
    export: true
  zcpc-processor-usage:
    export: true
  environmental-power-status:
    export: true
  cpc-resource:
    export: true
"""


TESTCASES_UPGRADE_CONFIG_FILE = [
    # Testcases for the test_upgrade_config_file() test function:
    # Each list item is a test case with the following tuple items:
    # - description (str): testcase description
    # - input_data (str): Content of input exporter config file
    # - exp_data (str): Expected content of upgraded exporter config file
    # - exp_stdout_patterns (list of str): Expected patterns of lines on stdout.
    # - exc_type (class): Exception class if failed, or None
    # - exc_pattern (str): Regexp for exception message if failed, or None

    (
        "Minimal version 1 config file, no comments",
        """metrics:
  hmc: 9.10.11.12
  userid: myuser
  password: mypassword
""",
        f"""version: 2
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: true
{DEFAULT_METRIC_GROUPS}
""",
        [
            r"^The exporter config file .* has the old version 1 format and "
            r"is now upgraded\.$",
            r"^Adding a 'metric_groups' item to the exporter configuration "
            r"that enables all metric groups\.$",
        ],
        None, None
    ),

    (
        "Maximum version 1 config file, no comments",
        """metrics:
  hmc: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: false
extra_labels:
- name: hmc
  value: HMC1
""",
        f"""version: 2
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: false
extra_labels:
- name: hmc
  value: HMC1
{DEFAULT_METRIC_GROUPS}
""",
        [
            r"^The exporter config file .* has the old version 1 format and "
            r"is now upgraded\.$",
            r"^Adding a 'metric_groups' item to the exporter configuration "
            r"that enables all metric groups\.$",
        ],
        None, None
    ),

    (
        "Version 1 config file with comments",
        """# exporter config file
metrics:
  hmc: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: false
extra_labels:
- name: hmc
  value: HMC1
""",
        f"""# exporter config file
version: 2
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: false
extra_labels:
- name: hmc
  value: HMC1
{DEFAULT_METRIC_GROUPS}
""",
        [
            r"^The exporter config file .* has the old version 1 format and "
            r"is now upgraded\.$",
            r"^Adding a 'metric_groups' item to the exporter configuration "
            r"that enables all metric groups\.$",
        ],
        None, None
    ),

    (
        "Version 2 config file without metric_groups",
        """version: 2
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: false
extra_labels:
- name: hmc
  value: HMC1
""",
        """version: 2
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: false
extra_labels:
- name: hmc
  value: HMC1
""",
        [
            r"^The exporter config file .* has the current version and is not "
            r"being changed\.$",
        ],
        None, None
    ),

    (
        "Version 2 config file without verify_cert",
        """version: 2
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
""",
        """version: 2
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
""",
        [
            r"^The exporter config file .* has the current version and is not "
            r"being changed\.$",
        ],
        None, None
    ),

    (
        "Version 2 config file with metric_groups",
        f"""version: 2
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
{DEFAULT_METRIC_GROUPS}
""",
        f"""version: 2
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
{DEFAULT_METRIC_GROUPS}
""",
        [
            r"^The exporter config file .* has the current version and is not "
            r"being changed\.$",
        ],
        None, None
    ),

    (
        "Invalid version 1 config file with missing 'metrics' item",
        """extra_labels:
- name: hmc
  value: HMC1
""",
        None,
        [],
        zhmc_prometheus_exporter.ImproperExit,
        r"^The exporter config file must specify either the new 'hmcs' item "
        r"or the old 'metrics' item, but it specifies none\.$"
    ),

    (
        "Invalid version 1 config file with both 'metrics' and 'hmcs' items",
        """metrics:
  hmc: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: false
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: false
""",
        None,
        [],
        zhmc_prometheus_exporter.ImproperExit,
        r"^The exporter config file must specify either the new 'hmcs' item "
        r"or the old 'metrics' item, but it specifies both\.$"
    ),

    (
        "Config file with unknown version",
        """version: 3
hmcs:
- host: 9.10.11.12
  userid: myuser
  password: mypassword
  verify_cert: false
""",
        None,
        [],
        zhmc_prometheus_exporter.ImproperExit,
        r"^The exporter config file must have the version 2 format, but it "
        r"specifies the version 3 format\.$"
    ),
]


@pytest.mark.parametrize(
    "description, input_data, exp_data, exp_stdout_patterns, "
    "exc_type, exc_pattern",
    TESTCASES_UPGRADE_CONFIG_FILE
)
def test_upgrade_config_file(
        # pylint: disable=unused-argument
        description, input_data, exp_data, exp_stdout_patterns,
        exc_type, exc_pattern,
        capsys):
    """
    Tests upgrade_config_file().
    """

    if sys.version_info[0:2] < (3, 12):
        pytest.skip("Testcase requires Python>=3.12")

    # Create the input exporter config file
    # pylint: disable=unexpected-keyword-arg
    with tempfile.NamedTemporaryFile(
            mode='w+', encoding='utf-8', delete_on_close=False) as fp:
        fp.write(input_data)
        fp.close()

        if exc_type is None:

            # The code to be tested
            zhmc_prometheus_exporter.upgrade_config_file(fp.name)

            # Check printed lines
            captured = capsys.readouterr()
            act_stdout_lines = captured.out.strip().split('\n')
            for i, act_line in enumerate(act_stdout_lines):
                exp_pattern = exp_stdout_patterns[i]
                assert re.search(exp_pattern, act_line) is not None
            assert captured.err == ""

            # Check the upgraded exporter config file
            with open(fp.name, encoding='utf-8') as exp_fp:
                act_data = exp_fp.read().strip()
            exp_data = exp_data.strip()
            assert act_data == exp_data, (
                "Unexpected data in upgraded exporter config file:\n"
                "\nActual file:\n"
                f"{act_data}\n"
                "\nExpected file:\n"
                f"{exp_data}\n"
            )

        else:
            with pytest.raises(exc_type) as exc_info:

                # The code to be tested
                zhmc_prometheus_exporter.upgrade_config_file(fp.name)

            exc = exc_info.value
            act_msg = str(exc)
            assert re.search(exc_pattern, act_msg) is not None
