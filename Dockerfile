# Dockerfile for zhmc-prometheus-exporter project
#
# This image runs the zhmc_prometheus_exporter command.
#
# The exporter config file needs to be made available to the container
# using some mount option and specified with -c.
#
# Example docker command to run the exporter using a locally built version of this image:
#
#   docker run --rm -v $(pwd)/myconfig:/root/myconfig -p 9291:9291 zhmc_prometheus_exporter -c /root/myconfig/config.yaml -v

FROM python:3.12-alpine as builder

# Path name of binary distribution archive of zhmc-prometheus-exporter package
ARG bdist_file
RUN : "${bdist_file:?Build argument bdist_file is required}"

# Install some packages onto this minimal Alpine image:
# - git - in case the Python requirements use git+https links
# - gcc musl-dev - in case Python wheels based on C need to be built (e.g. for rpds)
RUN apk add git gcc musl-dev

# Make sure the installed Python commands are found
ENV PATH=/root/.local/bin:$PATH

# Install the Python package of this project
COPY ${bdist_file} /tmp/${bdist_file}
RUN pip install --user /tmp/${bdist_file}

# Show the installed Linux packages
RUN echo "Installed Linux packages:" \
  && apk info -v

# Show the installed Python packages
RUN echo "Installed Python packages:" \
  && pip list

# Display files in 'rpds' Python package (verifying that it can be imported)
RUN echo "Files in rpds Python package:" \
  && python -c "import rpds, os, sys; rpds_dir=os.path.dirname(rpds.__file__); print(rpds_dir); sys.stdout.flush(); os.system(f'ls -al {rpds_dir}')"

# The Python 'rpds' package (used by 'jsonschema') has a shared library that is
# built during its installation, and thus depends on APIs of the system and
# the C library of the builder OS used in the first stage of this Dockerfile.
# Therefore, the OS used in the final stage needs to be compatible with the
# builder OS. We use the same OS image to make sure.
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
