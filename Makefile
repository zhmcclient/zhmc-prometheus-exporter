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

# Run type (normal, scheduled, release, local)
ifndef RUN_TYPE
  RUN_TYPE := local
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
  WHICH = which -a
endif

package_name := zhmc_prometheus_exporter

# Package version (e.g. "2.0.0a1.dev10+gd013028e" during development, or "2.0.0"
# when releasing).
# Note: The package version is automatically calculated by setuptools_scm based
# on the most recent tag in the commit history, increasing the least significant
# version indicator by 1.
package_version := $(shell $(PYTHON_CMD) -m setuptools_scm)

# Docker image
docker_image_name := zhmc_prometheus_exporter
docker_image_tag := latest

python_version := $(shell $(PYTHON_CMD) -c "import sys; sys.stdout.write('{}.{}'.format(sys.version_info[0], sys.version_info[1]))")
pymn := $(shell $(PYTHON_CMD) -c "import sys; sys.stdout.write('py{}{}'.format(sys.version_info[0], sys.version_info[1]))")

package_dir := $(package_name)

# The version file is recreated by setuptools-scm on every build, so it is
# excluded from git, and also from some dependency lists.
version_file := $(package_dir)/_version_scm.py

# Python files in the package, including any vendored packages, but excluding
# the $(version_file).
package_py_files := \
    $(filter-out $(version_file), $(wildcard $(package_dir)/*.py)) \
    $(wildcard $(package_dir)/*/*.py) \
    $(wildcard $(package_dir)/*/*/*.py) \
    $(wildcard $(package_dir)/*/*/*/*.py) \

test_dir := tests
test_py_files := \
    $(wildcard $(test_dir)/*.py) \
    $(wildcard $(test_dir)/*/*.py) \

dist_dir := dist
bdist_file := $(dist_dir)/$(package_name)-$(package_version)-py3-none-any.whl
sdist_file := $(dist_dir)/$(package_name)-$(package_version).tar.gz

# Dependencies of the distribution archives. Since the $(version_file) is
# created when building the distribution archives, this must not contain
# the $(version_file).
dist_dependent_files := \
    pyproject.toml \
    LICENSE \
    README.md \
    AUTHORS.md \
    requirements.txt \
    $(wildcard $(package_dir)/schemas/*.yaml) \
    $(wildcard $(package_dir)/data/*.yaml) \
    $(package_py_files) \

doc_dir := docs
doc_build_dir := build_docs
doc_build_file := $(doc_build_dir)/index.html
doc_dependent_files := \
    $(wildcard $(doc_dir)/*.*) \
    $(wildcard $(doc_dir)/*/*.*) \
    examples/config.yaml \
    $(package_py_files) \
    $(version_file) \

# Source files for checks (with PyLint and Flake8, etc.)
check_py_files := \
    $(filter-out $(version_file), $(wildcard $(package_dir)/*.py)) \
    $(test_py_files) \
    $(doc_dir)/conf.py \

# Directory for .done files
done_dir := done

# Packages whose dependencies are checked using pip-missing-reqs
check_reqs_packages := pip_check_reqs pipdeptree build pytest coverage coveralls flake8 ruff pylint safety bandit sphinx towncrier

# Ruff config file
ruff_rc_file := .ruff.toml

# Safety policy file
safety_install_policy_file := .safety-policy-install.yml
safety_develop_policy_file := .safety-policy-develop.yml

# Bandit config file
bandit_rc_file := .bandit.toml

ifdef TESTCASES
  pytest_opts := $(TESTOPTS) -k "$(TESTCASES)"
else
  pytest_opts := $(TESTOPTS)
endif

pytest_cov_rc_file := .coveragerc
pytest_cov_opts := --cov $(package_name) --cov-config $(pytest_cov_rc_file) --cov-append --cov-report=html

ifeq ($(PACKAGE_LEVEL),minimum)
  pip_level_opts := -c minimum-constraints-develop.txt -c minimum-constraints-install.txt
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
	@echo "  ruff       - Perform ruff checks (an alternate lint tool)"
	@echo "  pylint     - Perform pylint checks"
	@echo "  safety     - Run safety checker (for install and develop)"
	@echo "  bandit     - Run bandit checker"
	@echo "  test       - Perform unit tests (adds to coverage results)"
	@echo "  build      - Build the distribution files in $(dist_dir)"
	@echo "  builddoc   - Build the documentation in $(doc_build_dir)"
	@echo "  all        - Do all of the above"
	@echo "  release_branch - Create a release branch when releasing a version (requires VERSION and optionally BRANCH to be set)"
	@echo "  release_publish - Publish to PyPI when releasing a version (requires VERSION and optionally BRANCH to be set)"
	@echo "  start_branch - Create a start branch when starting a new version (requires VERSION and optionally BRANCH to be set)"
	@echo "  start_tag - Create a start tag when starting a new version (requires VERSION and optionally BRANCH to be set)"
	@echo "  docker     - Build local Docker image $(docker_image_name):$(docker_image_tag)"
	@echo "  authors    - Generate AUTHORS.md file from git log"
	@echo "  clean      - Remove any temporary files"
	@echo "  clobber    - Remove any build products"
	@echo "  platform   - Display the information about the platform as seen by make"
	@echo "  env        - Display the environment as seen by make"
	@echo 'Environment variables:'
	@echo "  TESTCASES=... - Testcase filter for pytest -k"
	@echo "  TESTOPTS=... - Additional options for pytest"
	@echo "  PACKAGE_LEVEL - Package level to be used for installing dependent Python"
	@echo "      packages in 'install' and 'develop' targets:"
	@echo "        latest - Latest package versions available on Pypi"
	@echo "        minimum - A minimum version as defined in minimum-constraints-*.txt"
	@echo "      Optional, defaults to 'latest'."
	@echo "  PYTHON_CMD=... - Name of python command. Default: python"
	@echo "  PIP_CMD=... - Name of pip command. Default: pip"
	@echo "  VERSION=... - M.N.U version to be released or started"
	@echo "  BRANCH=... - Name of branch to be released or started (default is derived from VERSION)"

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

.PHONY: _always
_always:

.PHONY: install
install: $(done_dir)/install_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: develop
develop: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: check
check: $(done_dir)/flake8_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: ruff
ruff: $(done_dir)/ruff_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: pylint
pylint: $(done_dir)/pylint_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: safety
safety: $(done_dir)/safety_develop_$(pymn)_$(PACKAGE_LEVEL).done $(done_dir)/safety_install_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: bandit
bandit: $(done_dir)/bandit_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: check_reqs
check_reqs: $(done_dir)/check_reqs_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

$(done_dir)/flake8_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(check_py_files)
	@echo "Makefile: Performing flake8 checks with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
	flake8 --config .flake8 $(check_py_files)
	echo "done" >$@
	@echo "Makefile: Done performing flake8 checks"

$(done_dir)/ruff_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(check_py_files)
	@echo "Makefile: Performing ruff checks with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
	ruff check --unsafe-fixes --config $(ruff_rc_file) $(check_py_files)
	echo "done" >$@
	@echo "Makefile: Done performing ruff checks"

$(done_dir)/pylint_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(check_py_files)
	@echo "Makefile: Performing pylint checks with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
	pylint --rcfile=.pylintrc --disable=fixme $(check_py_files)
	echo "done" >$@
	@echo "Makefile: Done performing pylint checks"

$(done_dir)/safety_develop_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(safety_develop_policy_file) minimum-constraints-develop.txt
	@echo "Makefile: Running Safety for development packages (and tolerate safety issues when RUN_TYPE is normal or scheduled)"
	-$(call RM_FUNC,$@)
	bash -c "safety check --policy-file $(safety_develop_policy_file) -r minimum-constraints-develop.txt --full-report || test '$(RUN_TYPE)' == 'normal' || test '$(RUN_TYPE)' == 'scheduled' || exit 1"
	echo "done" >$@
	@echo "Makefile: Done running Safety for development packages"

$(done_dir)/safety_install_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(safety_install_policy_file) minimum-constraints-install.txt
	@echo "Makefile: Running Safety for install packages (and tolerate safety issues when RUN_TYPE is normal)"
	-$(call RM_FUNC,$@)
	bash -c "safety check --policy-file $(safety_install_policy_file) -r minimum-constraints-install.txt --full-report || test '$(RUN_TYPE)' == 'normal' || exit 1"
	echo "done" >$@
	@echo "Makefile: Done running Safety for install packages"

$(done_dir)/bandit_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(bandit_rc_file) $(check_py_files)
	@echo "Makefile: Running Bandit"
	-$(call RM_FUNC,$@)
	bandit -c $(bandit_rc_file) -l $(check_py_files)
	echo "done" >$@
	@echo "Makefile: Done running Bandit"

$(done_dir)/check_reqs_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done minimum-constraints-develop.txt minimum-constraints-install.txt requirements.txt
	@echo "Makefile: Checking missing dependencies of this package"
	-$(call RM_FUNC,$@)
	pip-missing-reqs $(package_name) --requirements-file=requirements.txt
	pip-missing-reqs $(package_name) --requirements-file=minimum-constraints-install.txt
	@echo "Makefile: Done checking missing dependencies of this package"
ifeq ($(PLATFORM),Windows_native)
# Reason for skipping on Windows is https://github.com/r1chardj0n3s/pip-check-reqs/issues/67
	@echo "Makefile: Warning: Skipping the checking of missing dependencies of site-packages directory on native Windows" >&2
else
	@echo "Makefile: Checking missing dependencies of some development packages in our minimum versions"
	cat minimum-constraints-develop.txt minimum-constraints-install.txt >tmp_minimum-constraints.txt
	@rc=0; for pkg in $(check_reqs_packages); do dir=$$($(PYTHON_CMD) -c "import $${pkg} as m,os; dm=os.path.dirname(m.__file__); d=dm if not dm.endswith('site-packages') else m.__file__; print(d)"); cmd="pip-missing-reqs $${dir} --requirements-file=tmp_minimum-constraints.txt"; echo $${cmd}; $${cmd}; rc=$$(expr $${rc} + $${?}); done; exit $${rc}
	rm -f tmp_minimum-constraints.txt
	@echo "Makefile: Done checking missing dependencies of some development packages in our minimum versions"
endif
	echo "done" >$@

.PHONY: test
test: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(pytest_cov_rc_file)
	@echo "Makefile: Performing unit tests and coverage with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	@echo "Makefile: Note that the warning about an unknown metric is part of the tests"
	pytest $(pytest_cov_opts) -s $(test_dir) $(pytest_opts)
	@echo "Makefile: Done performing unit tests and coverage"
	@echo "Makefile: $@ done."

.PHONY: build
build: $(bdist_file) $(sdist_file)
	@echo "Makefile: $@ done."

.PHONY: builddoc
builddoc: $(doc_build_file)
	@echo "Makefile: $@ done."

.PHONY: all
all: install develop check_reqs check ruff pylint test build builddoc check_reqs safety bandit
	@echo "Makefile: $@ done."

.PHONY: release_branch
release_branch:
	@bash -c 'if [ -z "$(VERSION)" ]; then echo ""; echo "Error: VERSION env var is not set"; echo ""; false; fi'
	@bash -c 'if [ -n "$$(git status -s)" ]; then echo ""; echo "Error: Local git repo has uncommitted files:"; echo ""; git status; false; fi'
	git fetch origin
	@bash -c 'if [ -z "$$(git tag -l $(VERSION)a0)" ]; then echo ""; echo "Error: Release start tag $(VERSION)a0 does not exist (the version has not been started)"; echo ""; false; fi'
	@bash -c 'if [ -n "$$(git tag -l $(VERSION))" ]; then echo ""; echo "Error: Release tag $(VERSION) already exists (the version has already been released)"; echo ""; false; fi'
	@bash -c 'if [[ -n "$${BRANCH}" ]]; then echo $${BRANCH} >branch.tmp; elif [[ "$${VERSION#*.*.}" == "0" ]]; then echo "master" >branch.tmp; else echo "stable_$${VERSION%.*}" >branch.tmp; fi'
	@bash -c 'if [ -z "$$(git branch --contains $(VERSION)a0 $$(cat branch.tmp))" ]; then echo ""; echo "Error: Release start tag $(VERSION)a0 is not in target branch $$(cat branch.tmp), but in:"; echo ""; git branch --contains $(VERSION)a0;. false; fi'
	@echo "==> This will start the release of $(package_name) version $(VERSION) to PyPI using target branch $$(cat branch.tmp)"
	@echo -n '==> Continue? [yN] '
	@bash -c 'read answer; if [ "$$answer" != "y" ]; then echo "Aborted."; false; fi'
	bash -c 'git checkout $$(cat branch.tmp)'
	git pull
	@bash -c 'if [ -z "$$(git branch -l release_$(VERSION))" ]; then echo "Creating release branch release_$(VERSION)"; git checkout -b release_$(VERSION); fi'
	git checkout release_$(VERSION)
	make authors
	towncrier build --version $(VERSION) --yes
	git commit -asm "Release $(VERSION)"
	git push --set-upstream origin release_$(VERSION)
	rm -f branch.tmp
	@echo "Done: Pushed the release branch to GitHub - now go there and create a PR."
	@echo "Makefile: $@ done."

.PHONY: release_publish
release_publish:
	@bash -c 'if [ -z "$(VERSION)" ]; then echo ""; echo "Error: VERSION env var is not set"; echo ""; false; fi'
	@bash -c 'if [ -n "$$(git status -s)" ]; then echo ""; echo "Error: Local git repo has uncommitted files:"; echo ""; git status; false; fi'
	git fetch origin
	@bash -c 'if [ -n "$$(git tag -l $(VERSION))" ]; then echo ""; echo "Error: Release tag $(VERSION) already exists (the version has already been released)"; echo ""; false; fi'
	@bash -c 'if [[ -n "$${BRANCH}" ]]; then echo $${BRANCH} >branch.tmp; elif [[ "$${VERSION#*.*.}" == "0" ]]; then echo "master" >branch.tmp; else echo "stable_$${VERSION%.*}" >branch.tmp; fi'
	@bash -c 'if [ "$$(git log --format=format:%s origin/$$(cat branch.tmp)~..origin/$$(cat branch.tmp))" != "Release $(VERSION)" ]; then echo ""; echo "Error: Release PR for $(VERSION) has not been merged yet"; echo ""; false; fi'
	@echo "==> This will publish $(package_name) version $(VERSION) to PyPI using target branch $$(cat branch.tmp)"
	@echo -n '==> Continue? [yN] '
	@bash -c 'read answer; if [ "$$answer" != "y" ]; then echo "Aborted."; false; fi'
	bash -c 'git checkout $$(cat branch.tmp)'
	git pull
	git tag -f $(VERSION)
	git push -f --tags
	git branch -D release_$(VERSION)
	git branch -D -r origin/release_$(VERSION)
	rm -f branch.tmp
	@echo "Done: Triggered the publish workflow - now wait for it to finish and verify the publishing."
	@echo "Makefile: $@ done."

.PHONY: start_branch
start_branch:
	@bash -c 'if [ -z "$(VERSION)" ]; then echo ""; echo "Error: VERSION env var is not set"; echo ""; false; fi'
	@bash -c 'if [ -n "$$(git status -s)" ]; then echo ""; echo "Error: Local git repo has uncommitted files:"; echo ""; git status; false; fi'
	git fetch origin
	@bash -c 'if [ -n "$$(git tag -l $(VERSION))" ]; then echo ""; echo "Error: Release tag $(VERSION) already exists (the version has already been released)"; echo ""; false; fi'
	@bash -c 'if [ -n "$$(git tag -l $(VERSION)a0)" ]; then echo ""; echo "Error: Release start tag $(VERSION)a0 already exists (the new version has alreay been started)"; echo ""; false; fi'
	@bash -c 'if [ -n "$$(git branch -l start_$(VERSION))" ]; then echo ""; echo "Error: Start branch start_$(VERSION) already exists (the start of the new version is already underway)"; echo ""; false; fi'
	@bash -c 'if [[ -n "$${BRANCH}" ]]; then echo $${BRANCH} >branch.tmp; elif [[ "$${VERSION#*.*.}" == "0" ]]; then echo "master" >branch.tmp; else echo "stable_$${VERSION%.*}" >branch.tmp; fi'
	@echo "==> This will start new version $(VERSION) using target branch $$(cat branch.tmp)"
	@echo -n '==> Continue? [yN] '
	@bash -c 'read answer; if [ "$$answer" != "y" ]; then echo "Aborted."; false; fi'
	bash -c 'git checkout $$(cat branch.tmp)'
	git pull
	git checkout -b start_$(VERSION)
	echo "Dummy change for starting new version $(VERSION)" >changes/noissue.$(VERSION).notshown.rst
	git add changes/noissue.$(VERSION).notshown.rst
	git commit -asm "Start $(VERSION)"
	git push --set-upstream origin start_$(VERSION)
	@echo "Done: Pushed the start branch to GitHub - now go there and create a PR."
	@echo "Makefile: $@ done."

.PHONY: start_tag
start_tag:
	@bash -c 'if [ -z "$(VERSION)" ]; then echo ""; echo "Error: VERSION env var is not set"; echo ""; false; fi'
	@bash -c 'if [ -n "$$(git status -s)" ]; then echo ""; echo "Error: Local git repo has uncommitted files:"; echo ""; git status; false; fi'
	git fetch origin
	@bash -c 'if [ -n "$$(git tag -l $(VERSION)a0)" ]; then echo ""; echo "Error: Release start tag $(VERSION)a0 already exists (the new version has alreay been started)"; echo ""; false; fi'
	@bash -c 'if [[ -n "$${BRANCH}" ]]; then echo $${BRANCH} >branch.tmp; elif [[ "$${VERSION#*.*.}" == "0" ]]; then echo "master" >branch.tmp; else echo "stable_$${VERSION%.*}" >branch.tmp; fi'
	@bash -c 'if [ "$$(git log --format=format:%s origin/$$(cat branch.tmp)~..origin/$$(cat branch.tmp))" != "Start $(VERSION)" ]; then echo ""; echo "Error: Start PR for $(VERSION) has not been merged yet"; echo ""; false; fi'
	@echo "==> This will complete the start of new version $(VERSION) using target branch $$(cat branch.tmp)"
	@echo -n '==> Continue? [yN] '
	@bash -c 'read answer; if [ "$$answer" != "y" ]; then echo "Aborted."; false; fi'
	bash -c 'git checkout $$(cat branch.tmp)'
	git pull
	git tag -f $(VERSION)a0
	git push -f --tags
	git branch -D start_$(VERSION)
	git branch -D -r origin/start_$(VERSION)
	rm -f branch.tmp
	@echo "Done: Pushed the release start tag and cleaned up the release start branch."
	@echo "Makefile: $@ done."

.PHONY: docker
docker: $(done_dir)/docker_$(pymn)_$(PACKAGE_LEVEL).done
	@echo "Makefile: $@ done."

.PHONY: authors
authors: AUTHORS.md
	@echo "Makefile: $@ done."

# Make sure the AUTHORS.md file is up to date but has the old date when it did not change to prevent redoing dependent targets
AUTHORS.md: _always
	echo "# Authors of this project" >AUTHORS.md.tmp
	echo "" >>AUTHORS.md.tmp
	echo "Sorted list of authors derived from git commit history:" >>AUTHORS.md.tmp
	echo '```' >>AUTHORS.md.tmp
	sh -c "git shortlog --summary --email | cut -f 2 | sort >log.tmp"
	sh -c "ls -l log.tmp"
	sh -c "cat log.tmp >>AUTHORS.md.tmp"
	echo '```' >>AUTHORS.md.tmp
	sh -c "if ! grep -q '[^[:space:]]' log.tmp; then echo 'Warning - git shortlog does not display any authors - leaving AUTHORS.md file unchanged'; else if ! diff -q AUTHORS.md.tmp AUTHORS.md; then echo 'Updating AUTHORS.md as follows:'; diff AUTHORS.md.tmp AUTHORS.md; mv AUTHORS.md.tmp AUTHORS.md; else echo 'AUTHORS.md was already up to date'; fi; fi"
	sh -c "rm -f log.tmp AUTHORS.md.tmp"

.PHONY: clean
clean:
	-$(call RM_R_FUNC,*.pyc)
	-$(call RM_R_FUNC,*.tmp)
	-$(call RM_R_FUNC,tmp_*)
	-$(call RM_FUNC,.coverage MANIFEST MANIFEST.in AUTHORS ChangeLog)
	-$(call RMDIR_R_FUNC,__pycache__)
	-$(call RMDIR_R_FUNC,.ruff_cache)
	-$(call RMDIR_FUNC,build $(package_name).egg-info .pytest_cache)
	docker image prune --force
	@echo "Makefile: $@ done."

.PHONY: clobber
clobber: clean
	-$(call RMDIR_FUNC,$(doc_build_dir) htmlcov)
	-$(call RM_R_FUNC,*.done)
	@echo "Makefile: $@ done."

$(done_dir)/base_$(pymn)_$(PACKAGE_LEVEL).done: base-requirements.txt minimum-constraints-develop.txt minimum-constraints-install.txt
	@echo "Makefile: Installing base packages with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
	$(PYTHON_CMD) -m pip install $(pip_level_opts) -r base-requirements.txt
	@echo "Makefile: Done installing base packages"
	echo "done" >$@

$(done_dir)/install_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/base_$(pymn)_$(PACKAGE_LEVEL).done requirements.txt minimum-constraints-develop.txt minimum-constraints-install.txt pyproject.toml $(dist_dependent_files)
	@echo "Makefile: Installing package and its prerequisites with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
	$(PYTHON_CMD) -m pip install $(pip_level_opts) .
	@echo "Makefile: Done installing package and its prerequisites"
	echo "done" >$@

$(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/install_$(pymn)_$(PACKAGE_LEVEL).done dev-requirements.txt requirements.txt minimum-constraints-develop.txt minimum-constraints-install.txt
	@echo "Makefile: Installing prerequisites for development with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
	$(PYTHON_CMD) -m pip install $(pip_level_opts) -r dev-requirements.txt
	@echo "Makefile: Done installing prerequisites for development"
	echo "done" >$@

$(doc_build_file): $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done $(doc_dependent_files)
	@echo "Makefile: Generating HTML documentation with main file: $@"
	sphinx-build -b html -v $(doc_dir) $(doc_build_dir)
	@echo "Makefile: Done generating HTML documentation"

$(sdist_file): $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done pyproject.toml $(dist_dependent_files)
	@echo "Makefile: Building the source distribution archive: $(sdist_file)"
	$(PYTHON_CMD) -m build --sdist --outdir $(dist_dir) .
	@echo "Makefile: Done building the source distribution archive: $(sdist_file)"

$(bdist_file) $(version_file): $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done pyproject.toml $(dist_dependent_files)
	@echo "Makefile: Building the wheel distribution archive: $(bdist_file)"
	$(PYTHON_CMD) -m build --wheel --outdir $(dist_dir) -C--universal .
	@echo "Makefile: Done building the wheel distribution archive: $(bdist_file)"

$(done_dir)/docker_$(pymn)_$(PACKAGE_LEVEL).done: $(done_dir)/develop_$(pymn)_$(PACKAGE_LEVEL).done Dockerfile .dockerignore $(bdist_file)
	@echo "Makefile: Building Docker image $(docker_image_name):$(docker_image_tag)"
	-$(call RM_FUNC,$@)
	docker build --tag $(docker_image_name):$(docker_image_tag) --build-arg bdist_file=$(bdist_file) --build-arg package_version=$(subst +,.,$(package_version)) --build-arg build_date="$(shell date -Iseconds)" --build-arg git_commit="$(shell git rev-parse HEAD)" .
	docker run --rm $(docker_image_name):$(docker_image_tag) --version
	docker image list --filter reference=$(docker_image_name)
	@echo "Makefile: Done building Docker image"
	echo "done" >$@
