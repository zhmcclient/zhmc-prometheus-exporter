# Dockerfile for zhmc-prometheus-exporter project
#
# This image runs the zhmc_prometheus_exporter command.
# The standard metric definition file is provided in its default location, so
# the -m option does not need to be specified.
#
# The HMC credentials file still needs to be made available to the container
# using some mount option and specified with -c.
#
# Example docker command to run the exporter using a locally built version of this image:
#
#   docker run -it --rm -v $(pwd)/myconfig:/root/myconfig -p 9291:9291 zhmcexporter -c /root/myconfig/hmccreds.yaml -v

FROM python:3.9-slim

# Make the standard metric definition file available in its default location
COPY examples/metrics.yaml /etc/zhmc-prometheus-exporter/metrics.yaml

# Install this package
ENV TMP_DIR=/tmp/zhmc-prometheus-exporter
WORKDIR $TMP_DIR
COPY . $TMP_DIR

# TODO: Remove git install again once PR https://github.com/prometheus/client_python/pull/946 is released on Pypi
RUN apt-get update
RUN apt-get install -y --no-install-recommends git

RUN pip install . && rm -rf $TMP_DIR

# Set the current directory when running this image
WORKDIR /root

EXPOSE 9291
ENTRYPOINT ["zhmc_prometheus_exporter"]
CMD ["--help"]
