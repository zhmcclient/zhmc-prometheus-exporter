# Makefile for zhmc-prometheus-exporter project
#
# Use this to get information on the targets:
#   make  - or -  make help
#
# It is recommended to run this Makefile in a virtual Python environment,
# because Python packages will be installed automatically.
#
# Supported OS platforms:
#     Windows (native)
#     Linux (any)
#     macOS (OS-X)
#
# OS-level commands used by this Makefile (to be provided manually):
#   On native Windows:
#     cmd (providing: del, copy, rmdir, set)
#     where
#   On Linux and macOS:
#     rm, find, cp, env, sort, which, uname
#
# Environment variables:
#   PYTHON_CMD: Python command to use
#   PIP_CMD: Pip command to use
#   PACKAGE_LEVEL: minimum/latest - Level of Python dependent packages to use

# No built-in rules needed:
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

# Python / Pip commands
ifndef PYTHON_CMD
  PYTHON_CMD := python
endif
ifndef PIP_CMD
  PIP_CMD := pip
endif

# Package level
ifndef PACKAGE_LEVEL
  PACKAGE_LEVEL := latest
endif

# Determine OS platform make runs on.
ifeq ($(OS),Windows_NT)
  ifdef PWD
    PLATFORM := Windows_UNIX
  else
    PLATFORM := Windows_native
    ifndef COMSPEC
      # Make variables are case sensitive and some native Windows environments have
      # ComSpec set instead of COMSPEC.
      ifdef ComSpec
        COMSPEC = $(ComSpec)
      endif
    endif
    ifdef COMSPEC
      SHELL := $(subst \,/,$(COMSPEC))
    else
      SHELL := cmd.exe
    endif
    .SHELLFLAGS := /c
  endif
else
  # Values: Linux, Darwin
  PLATFORM := $(shell uname -s)
endif

ifeq ($(PLATFORM),Windows_native)
  # Note: The substituted backslashes must be doubled.
  # Remove files (blank-separated list of wildcard path specs)
  RM_FUNC = del /f /q $(subst /,\\,$(1))
  # Remove files recursively (single wildcard path spec)
  RM_R_FUNC = del /f /q /s $(subst /,\\,$(1))
  # Remove directories (blank-separated list of wildcard path specs)
  RMDIR_FUNC = rmdir /q /s $(subst /,\\,$(1))
  # Remove directories recursively (single wildcard path spec)
  RMDIR_R_FUNC = rmdir /q /s $(subst /,\\,$(1))
  # Copy a file, preserving the modified date
  CP_FUNC = copy /y $(subst /,\\,$(1)) $(subst /,\\,$(2))
  ENV = set
  WHICH = where
else
  RM_FUNC = rm -f $(1)
  RM_R_FUNC = find . -type f -name '$(1)' -delete
  RMDIR_FUNC = rm -rf $(1)
  RMDIR_R_FUNC = find . -type d -name '$(1)' | xargs -n 1 rm -rf
  CP_FUNC = cp -r $(1) $(2)
  ENV = env | sort
  WHICH = which
endif

package_name := zhmc_prometheus_exporter
package_version := $(shell $(PYTHON_CMD) setup.py --version)
docker_registry := zhmcexporter

python_version := $(shell $(PYTHON_CMD) -c "import sys; sys.stdout.write('{}.{}'.format(sys.version_info[0], sys.version_info[1]))")
pymn := $(shell $(PYTHON_CMD) -c "import sys; sys.stdout.write('py{}{}'.format(sys.version_info[0], sys.version_info[1]))")

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

# This is also used for 'include' statements in MANIFEST.in.
# Wildcards can be used directly (i.e. without wildcard function).
dist_included_files := \
    setup.py \
    LICENSE \
    README.rst \
    requirements.txt \
    $(package_py_files) \

doc_dir := docs
doc_build_dir := build_docs
doc_build_file := $(doc_build_dir)/index.html
doc_dependent_files := \
    $(wildcard $(doc_dir)/*.*) \
		$(wildcard $(doc_dir)/*/*.*) \
		examples/metrics.yaml \
		examples/hmccreds.yaml \
    $(package_py_files) \

# Directory for .done files
done_dir := done

# Packages whose dependencies are checked using pip-missing-reqs
check_reqs_packages := pip_check_reqs pipdeptree build pytest coverage coveralls flake8 pylint sphinx twine

# Safety policy file
safety_policy_file := .safety-policy.yml

pytest_cov_opts := --cov $(package_name) --cov-config .coveragerc --cov-append --cov-report=html:htmlcov
pytest_cov_files := .coveragerc

ifeq ($(PACKAGE_LEVEL),minimum)
  pip_level_opts := -c minimum-constraints.txt
else
  ifeq ($(PACKAGE_LEVEL),latest)
    pip_level_opts := --upgrade --upgrade-strategy eager
  else
    $(error Invalid value for PACKAGE_LEVEL variable: $(PACKAGE_LEVEL))
  endif
endif

.PHONY: help
help:
	@echo "Makefile for project $(package_name)"
	@echo "Package version: $(package_version)"
	@echo "Python version: $(python_version)"
	@echo "Targets:"
	@echo "  install    - Install package and its prerequisites"
	@echo "  develop    - Install prerequisites for development"
	@echo "  check_reqs - Perform missing dependency checks"
	@echo "  check      - Perform flake8 checks"
	@echo "  pylint     - Perform pylint checks"
	@echo "  safety     - Run safety on sources"
	@echo "  test       - Perform unit tests (adds to coverage results)"
	@echo "  build      - Build the distribution files in $(dist_dir)"
	@echo "  builddoc   - Build the documentation in $(doc_build_dir)"
	@echo "  all        - Do all of the above"
	@echo "  docker     - Build local Docker image in registry $(docker_registry)"
	@echo "  upload     - Upload the package to Pypi"
	@echo "  clean      - Remove any temporary files"
	@echo "  clobber    - Remove any build products"
	@echo "  platform   - Display the information about the platform as seen by make"
	@echo "  env        - Display the environment as seen by make"
	@echo 'Environment variables:'
	@echo "  PACKAGE_LEVEL - Package level to be used for installing dependent Python"
	@echo "      packages in 'install' and 'develop' targets:"
	@echo "        latest - Latest package versions available on Pypi"
	@echo "        minimum - A minimum version as defined in minimum-constraints.txt"
	@echo "      Optional, defaults to 'latest'."
	@echo '  PYTHON_CMD=... - Name of python command. Default: python'
	@echo '  PIP_CMD=... - Name of pip command. Default: pip'

.PHONY: platform
platform:
	@echo "Makefile: Platform information as seen by make:"
	@echo "Platform: $(PLATFORM)"
	@echo "Shell used for commands: $(SHELL)"
	@echo "Shell flags: $(.SHELLFLAGS)"
	@echo "Make version: $(MAKE_VERSION)"
	@echo "Python command name: $(PYTHON_CMD)"
	@echo "Python command location: $(shell $(WHICH) $(PYTHON_CMD))"
	@echo "Python version: $(python_version)"
	@echo "Pip command name: $(PIP_CMD)"
	@echo "Pip command location: $(shell $(WHICH) $(PIP_CMD))"
	@echo "Pip version: $(shell $(PIP_CMD) --version)"
	@echo "$(package_name) package version: $(package_version)"

.PHONY: env
env:
	@echo "Makefile: Environment variables as seen by make:"
	$(ENV)

.PHONY: _check_version
_check_version:
ifeq (,$(package_version))
	$(error Package version could not be determined)
endif

.PHONY: install
install: $(done_dir)/install_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: develop
develop: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: check
check: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: Performing flake8 checks with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	flake8 --config .flake8 $(package_py_files) $(test_py_files) setup.py $(doc_dir)/conf.py
	@echo "Makefile: Done performing flake8 checks"
	@echo "Makefile: $@ done."

.PHONY: pylint
pylint: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: Performing pylint checks with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	pylint --rcfile=.pylintrc --disable=fixme $(package_py_files) $(test_py_files) setup.py $(doc_dir)/conf.py
	@echo "Makefile: Done performing pylint checks"
	@echo "Makefile: $@ done."

.PHONY: safety
safety: $(done_dir)/safety_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: check_reqs
check_reqs: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done minimum-constraints.txt requirements.txt
	@echo "Makefile: Checking missing dependencies of this package"
# TODO-PYPI: Re-enable once a new version of prometheus-client (after 2023-11-09) has been released on Pypi
# pip-missing-reqs $(package_name) --requirements-file=requirements.txt
# pip-missing-reqs $(package_name) --requirements-file=minimum-constraints.txt
	@echo "Makefile: Done checking missing dependencies of this package"
ifeq ($(PLATFORM),Windows_native)
# Reason for skipping on Windows is https://github.com/r1chardj0n3s/pip-check-reqs/issues/67
	@echo "Makefile: Warning: Skipping the checking of missing dependencies of site-packages directory on native Windows" >&2
else
	@echo "Makefile: Checking missing dependencies of some development packages in our minimum versions"
	@rc=0; for pkg in $(check_reqs_packages); do dir=$$($(PYTHON_CMD) -c "import $${pkg} as m,os; dm=os.path.dirname(m.__file__); d=dm if not dm.endswith('site-packages') else m.__file__; print(d)"); cmd="pip-missing-reqs $${dir} --requirements-file=minimum-constraints.txt"; echo $${cmd}; $${cmd}; rc=$$(expr $${rc} + $${?}); done; exit $${rc}
	@echo "Makefile: Done checking missing dependencies of some development packages in our minimum versions"
endif
	@echo "Makefile: $@ done."

$(done_dir)/safety_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done Makefile $(safety_policy_file) minimum-constraints.txt
	@echo "Makefile: Running Safety"
	-$(call RM_FUNC,$@)
	safety check --policy-file $(safety_policy_file) -r minimum-constraints.txt --full-report
	echo "done" >$@
	@echo "Makefile: Done running Safety"

.PHONY: test
test: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(pytest_cov_files)
	@echo "Makefile: Performing unit tests and coverage with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	@echo "Makefile: Note that the warning about an unknown metric is part of the tests"
	pytest $(pytest_cov_opts) -s $(test_dir)
	@echo "Makefile: Done performing unit tests and coverage"
	@echo "Makefile: $@ done."

.PHONY: build
build: _check_version $(bdist_file) $(sdist_file)
	@echo "Makefile: $@ done."

.PHONY: builddoc
builddoc: _check_version $(doc_build_file)
	@echo "Makefile: $@ done."

.PHONY: all
all: install develop check_reqs check pylint test build builddoc check_reqs
	@echo "Makefile: $@ done."

.PHONY: all
docker: _check_version $(done_dir)/docker_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: upload
upload: _check_version $(bdist_file) $(sdist_file)
ifeq (,$(findstring .dev,$(package_version)))
	@echo "==> This will upload $(package_name) version $(package_version) to PyPI!"
	@echo -n "==> Continue? [yN] "
	@bash -c 'read answer; if [ "$$answer" != "y" ]; then echo "Aborted."; false; fi'
	twine upload $(bdist_file) $(sdist_file)
	@echo "Makefile: Done: Uploaded $(package_name) version to PyPI: $(package_version)"
else
	@echo "Error: A development version $(package_version) of $(package_name) cannot be uploaded to PyPI!"
	@false
endif

.PHONY: clean
clean:
	-$(call RM_R_FUNC,*.pyc)
	-$(call RM_R_FUNC,*.tmp)
	-$(call RM_R_FUNC,tmp_*)
	-$(call RM_FUNC,.coverage AUTHORS ChangeLog)
	-$(call RMDIR_R_FUNC,__pycache__)
	-$(call RMDIR_FUNC,build $(package_name).egg-info .pytest_cache)
	@echo "Makefile: $@ done."

.PHONY: clobber
clobber: clean
	-$(call RMDIR_FUNC,$(doc_build_dir) htmlcov)
	-$(call RM_R_FUNC,*.done)
	@echo "Makefile: $@ done."

$(done_dir)/install_base_$(pymn)_$(PACKAGE_LEVEL).done:
	@echo "Makefile: Installing base packages with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
	bash -c 'pv=$$($(PYTHON_CMD) -m pip --version); if [[ $$pv =~ (^pip [1-8]\..*) ]]; then $(PYTHON_CMD) -m pip install pip==9.0.1; fi'
	$(PYTHON_CMD) -m pip install $(pip_level_opts) pip setuptools wheel
	@echo "Makefile: Done installing base packages"
	echo "done" >$@

$(done_dir)/install_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/install_base_$(pymn)_$(PACKAGE_LEVEL).done requirements.txt setup.py
	@echo "Makefile: Installing package and its prerequisites with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
	$(PYTHON_CMD) -m pip install $(pip_level_opts) -e .
	@echo "Makefile: Done installing package and its prerequisites"
	echo "done" >$@

$(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/install_$(pymn)_$(PACKAGE_LEVEL).done dev-requirements.txt
	@echo "Makefile: Installing prerequisites for development with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
	$(PYTHON_CMD) -m pip install $(pip_level_opts) -r dev-requirements.txt
	@echo "Makefile: Done installing prerequisites for development"
	echo "done" >$@

$(doc_build_file): $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(doc_dependent_files)
	@echo "Makefile: Generating HTML documentation with main file: $@"
	sphinx-build -b html -v $(doc_dir) $(doc_build_dir)
	@echo "Makefile: Done generating HTML documentation"

# Note: distutils depends on the right files specified in MANIFEST.in, even when
# they are already specified e.g. in 'package_data' in setup.py.
# We generate the MANIFEST.in file automatically, to have a single point of
# control (this Makefile) for what gets into the distribution archive.
MANIFEST.in: Makefile $(dist_included_files)
	@echo "Makefile: Creating the manifest input file"
	echo "# MANIFEST.in file generated by Makefile - DO NOT EDIT!!" >$@
ifeq ($(PLATFORM),Windows_native)
	for %%f in ($(dist_included_files)) do (echo include %%f >>$@)
else
	echo "$(dist_included_files)" | xargs -n 1 echo include >>$@
endif
	@echo "Makefile: Done creating the manifest input file: $@"

# Distribution archives.
# Note: Deleting MANIFEST causes distutils (setup.py) to read MANIFEST.in and to
# regenerate MANIFEST. Otherwise, changes in MANIFEST.in will not be used.
# Note: Deleting build is a safeguard against picking up partial build products
# which can lead to incorrect hashbangs in scripts in wheel archives.
$(bdist_file) $(sdist_file): _check_version $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done Makefile MANIFEST.in $(dist_included_files)
	-$(call RM_FUNC,MANIFEST)
	-$(call RMDIR_FUNC,build $(package_name).egg-info .eggs)
	$(PYTHON_CMD) -m build --outdir $(dist_dir)
	@echo 'Done: Created distribution archives: $@'

$(done_dir)/docker_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done Dockerfile .dockerignore Makefile MANIFEST.in $(dist_included_files)
	@echo "Makefile: Building Docker image $(docker_registry):latest"
	-$(call RM_FUNC,$@)
	docker build -t $(docker_registry):latest .
	@echo "Makefile: Done building Docker image"
	echo "done" >$@
