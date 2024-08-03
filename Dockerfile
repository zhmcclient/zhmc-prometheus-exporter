# Dockerfile for zhmc-prometheus-exporter project
#
# This image runs the zhmc_prometheus_exporter command.
#
# The exporter config file needs to be made available to the container
# using some mount option and specified with -c.
#
# Example docker command to run the exporter using a locally built version of this image:
#
#   docker run -it --rm -v $(pwd)/myconfig:/root/myconfig -p 9291:9291 zhmcexporter:2.0.0 -c /root/myconfig/config.yaml -v

FROM python:3.12-slim as builder

# Path name of binary distribution archive of zhmc-prometheus-exporter package
ARG bdist_file
RUN : "${bdist_file:?Build argument bdist_file is required}"

# Install git in case the requirements use git+https links.
RUN apt-get update \
  && apt-get install -y --no-install-recommends git

# Install the zhmc-prometheus-exporter package
COPY ${bdist_file} /tmp/${bdist_file}
RUN pip install --user /tmp/${bdist_file} \
  && rm -f /tmp/${bdist_file} \
  && pip list

# Uninstall Python packages not needed for running the package
RUN python -m pip uninstall -y pip setuptools wheel

FROM python:3.12-alpine

# Version of the zhmc-prometheus-exporter package
ARG package_version
RUN : "${package_version:?Build argument package_version is required}"

# Image build date in ISO-8601 format
ARG build_date
RUN : "${build_date:?Build argument build_date is required}"

# Git commit ID of the zhmc-prometheus-exporter repo used to build the image
ARG git_commit
RUN : "${git_commit:?Build argument git_commit is required}"

# Set image metadata
LABEL org.opencontainers.image.title="IBM Z HMC Prometheus Exporter"
LABEL org.opencontainers.image.version="${package_version}"
LABEL org.opencontainers.image.authors="Andreas Maier, Kathir Velusamy"
LABEL org.opencontainers.image.created="${build_date}"
LABEL org.opencontainers.image.url="https://github.com/zhmcclient/zhmc-prometheus-exporter"
LABEL org.opencontainers.image.documentation="https://zhmc-prometheus-exporter.readthedocs.io"
LABEL org.opencontainers.image.source="https://github.com/zhmcclient/zhmc-prometheus-exporter"
LABEL org.opencontainers.image.licenses="Apache Software License 2.0"
LABEL org.opencontainers.image.revision="${git_commit}"

# Copy the installed Python packages from the builder image
COPY --from=builder /root/.local /root/.local

# Make sure the installed Python commands are found
ENV PATH=/root/.local/bin:$PATH

EXPOSE 9291
ENTRYPOINT ["zhmc_prometheus_exporter"]
CMD ["--help"]
