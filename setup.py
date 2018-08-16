# Copyright 2018 IBM Corp. All Rights Reserved.
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

"""Set up project for pip."""

import setuptools

setuptools.setup(
    name="zhmc_prometheus_exporter",
    version="0.1",
    description="A prometheus.io exporter for metrics from the IBM Z HMC",
    url="https://github.com/zhmcclient/zhmc-prometheus-exporter"
    author="Jakob Naucke",
    author_email="jakob.naucke@ibm.com",
    license="Apache-2.0",
    long_description="Please see README.rst",
    platforms="Linux",
    packages=["zhmc_prometheus_exporter"],
    install_requires=["pyyaml>=3.13",
                      "zhmcclient>=0.19.0",
                      "prometheus-client>=0.3.1"],
    entry_points={"console_scripts": ["zhmc_prometheus_exporter = "
                                      "zhmc_prometheus_exporter."
                                      "zhmc_prometheus_exporter:main"]}
)
