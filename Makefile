# Makefile for zhmc_prometheus exporter
# Prerequisites:
#   OS: Linux, macOS
#   Commands provided by the OS:
#     bash
#     find
#     make
#     pip
#     python
#     rm
# Use this to get information on the targets:
#   make help

package_name := zhmc_prometheus_exporter
package_version := $(shell python -c "from pbr.version import VersionInfo; vi=VersionInfo('$(package_name)'); print(vi.release_string())" 2> /dev/null)

python_version := $(shell python -c "import sys; sys.stdout.write('%s.%s'%(sys.version_info[0], sys.version_info[1]))")
pymn := $(shell python -c "import sys; sys.stdout.write('py%s%s'%(sys.version_info[0], sys.version_info[1]))")

package_dir := $(package_name)
package_py_files := \
    $(wildcard $(package_dir)/*.py) \
    $(wildcard $(package_dir)/*/*.py) \

test_dir := tests
test_py_files := \
    $(wildcard $(test_dir)/*.py) \
    $(wildcard $(test_dir)/*/*.py) \

dist_dir := dist
bdist_file := $(dist_dir)/$(package_name)-$(package_version)-py2.py3-none-any.whl
sdist_file := $(dist_dir)/$(package_name)-$(package_version).tar.gz

doc_dir := docs
doc_build_dir := build_docs
doc_build_file := $(doc_build_dir)/html/index.html
doc_dependent_files := \
    $(doc_dir)/conf.py \
    $(wildcard $(doc_dir)/*.rst) \
    $(package_py_files) \

ifeq ($(python_version),3.4)
  pytest_cov_opts :=
else
  pytest_cov_opts := --cov $(package_name) --cov-config .coveragerc --cov-report=html:htmlcov
endif

.PHONY: help
help:
	@echo "Makefile for project $(package_name)"
	@echo "Package version: $(package_version)"
	@echo "Python version: $(python_version)"
	@echo "Targets:"
	@echo "  install    - Install package and its prerequisites"
	@echo "  develop    - Install prerequisites for development"
	@echo "  check      - Perform flake8 checks"
	@echo "  pylint     - Perform pylint checks"
	@echo "  test       - Perform unit tests including coverage checker"
	@echo "  build      - Build the distribution files in $(dist_dir)"
	@echo "  builddoc   - Build the documentation in $(doc_build_file)"
	@echo "  all        - Do all of the above"
	@echo "  upload     - Upload the package to Pypi"
	@echo "  clean      - Remove any temporary files"
	@echo "  clobber    - Remove any build products"

.PHONY: _check_version
_check_version:
ifeq (,$(package_version))
	@echo 'Error: Package version could not be determine: (requires pbr; run "make develop")'
	@false
else
	@true
endif

.PHONY: install
install: install_$(pymn).done
	@echo "$@ done."

.PHONY: develop
develop: develop_$(pymn).done
	@echo "$@ done."

.PHONY: check
check: develop_$(pymn).done
	@echo "Performing flake8 checks..."
	flake8 --config .flake8 $(package_py_files) $(test_py_files) setup.py $(doc_dir)/conf.py
	@echo "$@ done."

.PHONY: pylint
pylint: develop_$(pymn).done
	@echo "Performing pylint checks..."
	pylint --rcfile=.pylintrc $(package_py_files) $(test_py_files) setup.py $(doc_dir)/conf.py
	@echo "$@ done."

.PHONY: test
test: develop_$(pymn).done
	@echo "Performing unit tests including coverage checker..."
	@echo "Note that the warning about an unknown metric is part of the tests"
	pytest $(pytest_cov_opts) -s $(test_dir)
	@echo "$@ done."

.PHONY: build
build: _check_version $(bdist_file) $(sdist_file)
	@echo "$@ done."

.PHONY: builddoc
builddoc: _check_version $(doc_build_file)
	@echo "$@ done."

.PHONY: all
all: install develop check pylint test build builddoc
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

.PHONY: clean
clean:
	@echo "Removing any temporary files..."
	rm -rfv build $(package_name).egg-info .pytest_cache .coverage $(test_dir)/__pycache__ $(package_dir)/__pycache__ AUTHORS ChangeLog
	find . -type f -name '*.pyc' -delete
	@echo "$@ done."

.PHONY: clobber
clobber: clean
	@echo "Removing any build products..."
	rm -rfv dist $(doc_build_dir) htmlcov
	rm -rfv *.done
	@echo "$@ done."

install_base_$(pymn).done:
	@echo "Installing base packages..."
	rm -f $@
	python -m pip install --upgrade --upgrade-strategy eager pip setuptools wheel
	@echo "Done: Installed base packages"
	echo "done" >$@

install_$(pymn).done: install_base_$(pymn).done requirements.txt setup.py setup.cfg
	@echo "Installing package and its prerequisites..."
	rm -f $@
	pip install --upgrade-strategy eager -r requirements.txt
	pip install -e .
	@echo "Done: Installed package and its prerequisites"
	echo "done" >$@

develop_$(pymn).done: install_$(pymn).done dev-requirements.txt
	@echo "Installing prerequisites for development..."
	rm -f $@
	pip install --upgrade-strategy eager -r dev-requirements.txt
	@echo "Done: Installed prerequisites for development"
	echo "done" >$@

$(doc_build_file): develop_$(pymn).done
ifeq ($(python_version),3.4)
	@echo "Warning: Skipping Sphinx doc build on Python $(python_version)" >&2
else
	@echo "Generating HTML documentation..."
	sphinx-build -b html $(doc_dir) $(doc_build_dir)
	@echo "Done: Generated HTML documentation with main file: $@"
endif

$(bdist_file): _check_version develop_$(pymn).done
	@echo "Creating binary distribution archive $@..."
	python setup.py bdist_wheel -d $(dist_dir) --universal
	@echo "Done: Created binary distribution archive $@."

$(sdist_file): _check_version develop_$(pymn).done
	@echo "Creating source distribution archive $@..."
	python setup.py sdist -d $(dist_dir)
	@echo "Done: Created source distribution archive $@."
