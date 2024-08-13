Improved build of the Docker image: It now uses the package version as the
image tag, sets OCI metadata as labels, and reduces the image size by using
the python:3.12-alpine base image, building from the Python distribution
archive instead of copying the repo, uninstalling pip, setuptools and
wheel since they are not needed to run the exporter, and using a multi-staged
build to copy just the installed Python packages. This reduced the image file
size with Docker on Ubuntu from 256 MB to 73 MB.
