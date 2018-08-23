# Makefile for zhmc_prometheus exporter
# Prerequisites:
#   Any Linux distribution (macOS not officially supported)
#   All of these commands:
#     bash
#     rm
#     make
#     python3
#     pip3
# Use this to get information on the targets:
#   make help

package_name := zhmc_prometheus_exporter
package_version := $(shell python3 -c "from pbr.version import VersionInfo; vi=VersionInfo('$(package_name)'); print(vi.release_string())" 2> /dev/null)
python_version := $(shell python3 -c "import sys; sys.stdout.write('%s.%s'%(sys.version_info[0], sys.version_info[1]))")

package_dir := zhmc_prometheus_exporter
package_file := zhmc_prometheus_exporter.py
test_dir := zhmc_prometheus_exporter
test_file := test.py

dist_dir := dist
bdist_file := $(dist_dir)/$(package_name)-$(package_version)-py2.py3-none-any.whl
sdist_file := $(dist_dir)/$(package_name)-$(package_version).tar.gz

doc_dir := docs
build_doc_dir := $(doc_dir)/_build

.PHONY: help
help:
	@echo "Makefile for project $(package_name)"
	@echo "Package version: $(package_version)"
	@echo "Python version: $(python_version)"
	@echo "Targets:"
	@echo "  setup       - Install prerequisites"
	@echo "  install     - Install package"
	@echo "  uninstall   - Uninstall package"
	@echo "  dev-setup   - Install building & testing prerequisites"
	@echo "  build       - Build the distribution files in $(dist_dir)"
	@echo "                Binary: $(bdist_file)"
	@echo "                Source: $(sdist_file)"
	@echo "  builddoc    - Build the documentation in $(build_doc_dir)/index.html"
	@echo "  test        - Perform unit tests including coverage checker"
	@echo "  lint        - Perform lint tests"
	@echo "  clean       - Clean up temporary files"
	@echo "  clean-built - Clean up files that the build processes generated"

.PHONY: _check_version
_check_version:
ifeq (,$(package_version))
	@echo 'Error: Package version could not be determine: (requires pbr; run "make dev-setup")'
	@false
else
	@true
endif

.PHONY: setup
setup:
	@echo "Installing requirements..."
	pip3 install -r requirements.txt
	@echo "$@ done."

.PHONY: install
install:
	@echo "Installing $(package_name)..."
	pip3 install .
	@echo "$@ done."

.PHONY: uninstall
uninstall:
	@echo "Uninstalling $(package_name)..."
	bash -c "pip3 show $(package_name) > /dev/null; if [ $$? -eq 0 ]; then pip3 uninstall -y $(package_name); fi"
	@echo "$@ done."

.PHONY: dev-setup
dev-setup: setup
	@echo "Installing dev requirements..."
	pip3 install -r dev-requirements.txt
	@echo "$@ done."

.PHONY: upload
upload: _check_version $(bdist_file) $(sdist_file)
ifeq (,$(findstring .dev,$(package_version)))
	@echo "==> This will upload $(package_name) version $(package_version) to PyPI!"
	@echo -n "==> Continue? [yN] "
	@bash -c 'read answer; if [ "$$answer" != "y" ]; then echo "Aborted."; false; fi'
	twine upload $(bdist_file) $(sdist_file)
	@echo "Done: Uploaded $(package_name) version to PyPI: $(package_version)"
else
	@echo "Error: A development version $(package_version) of $(package_name) cannot be uploaded to PyPI!"
	@false
endif

.PHONY: builddoc
builddoc: html
	@echo "Building HTML documentation..."
	@echo "$@ done."

.PHONY: build
build: $(bdist_file) $(sdist_file)
	@echo "Building binary & source distributions..."
	@echo "$@ done."

.PHONY: test
test: dev-setup install
	@echo "Performing unit tests of $(package_name) with coverage checker..."
	@echo "Note that the warning about an unknown metric is part of the tests"
	py.test $(test_dir)/$(test_file) --cov $(package_name) --cov-report=html
	@echo "$@ done."

.PHONY: lint
lint: dev-setup
	@echo "Performing lint tests of $(package_name)..."
	flake8
	@echo "$@ done."

.PHONY: clean
clean:
	@echo "Cleaning up temporary files..."
	rm -rfv build $(package_name).egg-info .pytest_cache .coverage $(test_dir)/__pycache__ AUTHORS ChangeLog
	@echo "$@ done."

.PHONY: clean-built
clean-built:
	@echo "Cleaning up built files..."
	rm -rfv dist docs/_build htmlcov
	@echo "$@ done."

html: dev-setup
	@echo "Generating an HTML documentation..."
	sphinx-build -b html $(doc_dir) $(build_doc_dir)
	@echo "$@ done."

$(bdist_file): dev-setup clean
	@echo "Creating binary distribution archive $@..."
	python3 setup.py bdist_wheel -d $(dist_dir) --universal
	@echo "Done: Created binary distribution archive $@."

$(sdist_file): dev-setup clean
	@echo "Creating source distribution archive $@..."
	python3 setup.py sdist -d $(dist_dir)
	@echo "Done: Created source distribution archive $@."
