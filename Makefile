# Makefile for zhmc_prometheus exporter
# Prerequisites:
#   OS: Linux, macOS, Windows
#   Commands provided by Linux, macOS:
#     make
#     pip
#     python
#     bash
#     find
#     rm
#   Commands provided by Windows:
#     make
#     pip
#     python
#     del
#     rmdir
# Use this to get information on the targets:
#   make help

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

doc_dir := docs
doc_build_dir := build_docs
doc_build_file := $(doc_build_dir)/index.html
doc_dependent_files := \
    $(wildcard $(doc_dir)/*.*) \
		$(wildcard $(doc_dir)/*/*.*) \
		examples/metrics.yaml \
		examples/hmccreds.yaml \
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
	@echo "  builddoc   - Build the documentation in $(doc_build_dir)"
	@echo "  all        - Do all of the above"
	@echo "  upload     - Upload the package to Pypi"
	@echo "  clean      - Remove any temporary files"
	@echo "  clobber    - Remove any build products"
	@echo "  platform   - Display the information about the platform as seen by make"
	@echo "  env        - Display the environment as seen by make"

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
	@echo "Error: Package version could not be determined"
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
	-$(call RM_R_FUNC,*.pyc)
	-$(call RM_R_FUNC,*.tmp)
	-$(call RM_R_FUNC,tmp_*)
	-$(call RM_FUNC,.coverage AUTHORS ChangeLog)
	-$(call RMDIR_R_FUNC,__pycache__)
	-$(call RMDIR_FUNC,build $(package_name).egg-info .pytest_cache)
	@echo "$@ done."

.PHONY: clobber
clobber: clean
	-$(call RMDIR_FUNC,$(doc_build_dir) htmlcov)
	-$(call RM_FUNC,*.done)
	@echo "$@ done."

install_base_$(pymn).done:
	@echo "Installing base packages..."
	-$(call RM_FUNC,$@)
	bash -c 'pv=$$(python -m pip --version); if [[ $$pv =~ (^pip [1-8]\..*) ]]; then python -m pip install pip==9.0.1; fi'
	python -m pip install --upgrade pip setuptools wheel
	@echo "Done: Installed base packages"
	echo "done" >$@

install_$(pymn).done: install_base_$(pymn).done requirements.txt setup.py
	@echo "Installing package and its prerequisites..."
	-$(call RM_FUNC,$@)
	pip install --upgrade-strategy eager -r requirements.txt
	pip install -e .
	@echo "Done: Installed package and its prerequisites"
	echo "done" >$@

develop_$(pymn).done: install_$(pymn).done dev-requirements.txt
	@echo "Installing prerequisites for development..."
	-$(call RM_FUNC,$@)
	pip install --upgrade-strategy eager -r dev-requirements.txt
	@echo "Done: Installed prerequisites for development"
	echo "done" >$@

$(doc_build_file): develop_$(pymn).done $(doc_dependent_files)
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
