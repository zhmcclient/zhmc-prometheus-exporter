FROM python:3
MAINTAINER Jakob Naucke <jakob.naucke@ibm.com>

COPY zhmc_prometheus_exporter/zhmc_prometheus_exporter.py /usr/local/zhmc_prometheus_exporter.py
COPY requirements.txt /etc/zhmc-prometheus-exporter/requirements.txt
COPY hmccreds.yaml /etc/zhmc-prometheus-exporter/hmccreds.yaml
COPY metrics.yaml /etc/zhmc-prometheus-exporter/metrics.yaml

RUN pip install -r /etc/zhmc-prometheus-exporter/requirements.txt
EXPOSE 9291
ENTRYPOINT ["python", "/usr/local/zhmc_prometheus_exporter.py"]
