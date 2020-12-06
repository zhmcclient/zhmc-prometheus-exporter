FROM python:3
MAINTAINER Jakob Naucke <jakob.naucke@ibm.com>

# Attention: You need to provide an HMC credentials file for your target environment:
COPY myconfig/hmccreds.yaml /etc/zhmc-prometheus-exporter/hmccreds.yaml

# Attention: You need to provide a metric definition file (e.g. the one from the examples directory):
COPY myconfig/metrics.yaml /etc/zhmc-prometheus-exporter/metrics.yaml

COPY zhmc_prometheus_exporter/ /usr/local/
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

EXPOSE 9291
ENTRYPOINT ["python", "/usr/local/zhmc_prometheus_exporter.py"]
