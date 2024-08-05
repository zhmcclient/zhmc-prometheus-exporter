# IBM Z HMC Prometheus Exporter

[![Version on Pypi](https://img.shields.io/pypi/v/zhmc-prometheus-exporter.svg)](https://pypi.python.org/pypi/zhmc-prometheus-exporter/)
[![Test status (master)](https://github.com/zhmcclient/zhmc-prometheus-exporter/actions/workflows/test.yml/badge.svg?branch=master)](https://github.com/zhmcclient/zhmc-prometheus-exporter/actions/workflows/test.yml?query=branch%3Amaster)
[![Docs status (master)](https://readthedocs.org/projects/zhmc-prometheus-exporter/badge/?version=latest)](https://readthedocs.org/projects/zhmc-prometheus-exporter/builds/)
[![Test coverage (master)](https://coveralls.io/repos/github/zhmcclient/zhmc-prometheus-exporter/badge.svg?branch=master)](https://coveralls.io/github/zhmcclient/zhmc-prometheus-exporter?branch=master)

The **IBM Z HMC Prometheus Exporter** is a
[Prometheus exporter](https://prometheus.io/docs/instrumenting/exporters)
written in Python that retrieves metrics from the
[IBM Z](https://www.ibm.com/it-infrastructure/z) Hardware Management Console
(HMC) and exports them to the [Prometheus](https://prometheus.io)
monitoring system.

The exporter supports all metrics provided by the Z HMC and in addition
a number of useful metrics that are based on properties of HMC resources
(e.g. memory or CPU weight of LPARs). The resource property based
metrics are obtained in the background via change notifications emitted
by the HMC and via asynchronous retrieval for properties where change
notifications are not supported. This keeps the time for providing the
metric data to Prometheus short (sub-second to a few seconds).

The exporter attempts to stay up as much as possible, for example it
performs automatic session renewals with the HMC if the logon session
expires, and it survives HMC reboots and automatically picks up metrics
collection again once the HMC come back up.

# Documentation

- [Documentation](https://zhmc-prometheus-exporter.readthedocs.io/en/stable/)
- [Change log](https://zhmc-prometheus-exporter.readthedocs.io/en/stable/changes.html)

# Quickstart

- Install the exporter and all of its Python dependencies as follows:

  ``` bash
  $ pip install zhmc-prometheus-exporter
  ```

- Provide an *HMC credentials file* for use by the exporter.

  The HMC credentials file tells the exporter which HMC to talk to for
  obtaining metrics, and which userid and password to use for logging
  on to the HMC.

  It also defines whether HTTP or HTTPS is used for Prometheus, and
  HTTPS related certificates and keys.

  Download the
  [sample HMC credentials file](https://zhmc-prometheus-exporter.readthedocs.io/en/stable/usage.html#sample-hmc-credentials-file)
  as `hmccreds.yaml` and edit that copy accordingly.

  For details, see
  [HMC credentials file](https://zhmc-prometheus-exporter.readthedocs.io/en/stable/usage.html#hmc-credentials-file).

- Provide a *metric definition file* for use by the exporter.

  The metric definition file maps the metrics returned by the HMC to
  metrics exported to Prometheus.

  Furthermore, the metric definition file allows optimizing the access
  time to the HMC by disabling the fetching of metrics that are not
  needed.

  Download the [sample metric definition
  file](https://zhmc-prometheus-exporter.readthedocs.io/en/stable/usage.html#sample-metric-definition-file)
  as `metrics.yaml`. It can be used as it is and will have all metrics
  enabled and mapped properly. You only need to edit the file if you
  want to adjust the metric names, labels, or metric descriptions, or
  if you want to optimize access time by disabling metrics not needed.

  For details, see [Metric definition
  file](https://zhmc-prometheus-exporter.readthedocs.io/en/stable/usage.html#metric-definition-file).

- Run the exporter as follows:

  ``` bash
  $ zhmc_prometheus_exporter -c hmccreds.yaml -m metrics.yaml
  Exporter is up and running on port 9291
  ```

  Depending on the number of CPCs managed by your HMC, and dependent
  on how many metrics are enabled, it will take some time until the
  exporter reports to be up and running. You can see what it does in
  the mean time by using the `-v` option. Subsequent requests to the
  exporter will be sub-second.

- Direct your web browser at <http://localhost:9291> (or
  <https://localhost:9291> when using HTTPS) to see the exported
  Prometheus metrics. Refreshing the browser will update the metrics.

# Reporting issues

If you encounter a problem, please report it as an
[issue on GitHub](https://github.com/zhmcclient/zhmc-prometheus-exporter/issues).

# License

This package is licensed under the
[Apache 2.0 License](http://apache.org/licenses/LICENSE-2.0).
