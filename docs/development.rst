.. Copyright 2018 IBM Corp. All Rights Reserved.
..
.. Licensed under the Apache License, Version 2.0 (the "License");
.. you may not use this file except in compliance with the License.
.. You may obtain a copy of the License at
..
..    http://www.apache.org/licenses/LICENSE-2.0
..
.. Unless required by applicable law or agreed to in writing, software
.. distributed under the License is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.

Development
===========

This page covers the relevant aspects for developers.

Repository
----------

The Git repository for the exporter project is GitHub:
https://github.com/zhmcclient/zhmc-prometheus-exporter

Code of Conduct
---------------

Contribution must follow the `Code of Conduct as defined by the Contributor Covenant`_.

.. _Code of Conduct as defined by the Contributor Covenant: https://www.contributor-covenant.org/version/1/4/code-of-conduct

Contributing
------------

Third party contributions to this project are welcome!

In order to contribute, create a `Git pull request`_, considering this:

.. _Git pull request: https://help.github.com/articles/using-pull-requests/

* Test is required.
* Each commit should only contain one "logical" change.
* A "logical" change should be put into one commit, and not split over multiple
  commits.
* Large new features should be split into stages.
* The commit message should not only summarize what you have done, but explain
  why the change is useful.
* The commit message must follow the format explained below.

What comprises a "logical" change is subject to sound judgement. Sometimes, it
makes sense to produce a set of commits for a feature (even if not large). For
example, a first commit may introduce a (presumably) compatible API change
without exploitation of that feature. With only this commit applied, it should
be demonstrable that everything is still working as before. The next commit may
be the exploitation of the feature in other components.

For further discussion of good and bad practices regarding commits, see:

* `OpenStack Git Commit Good Practice`_
* `How to Get Your Change Into the Linux Kernel`_

.. _OpenStack Git Commit Good Practice: https://wiki.openstack.org/wiki/GitCommitMessages
.. _How to Get Your Change Into the Linux Kernel: https://www.kernel.org/doc/Documentation/SubmittingPatches


.. _`Making a change`:

Making a change
---------------

To make a change, create a topic branch. You can assume that you are the only
one using that branch, so force-pushes to that branch and rebasing that branch
is fine.

When you are ready to push your change, describe the change for users of the
package in a change fragment file. To create a change fragment file, execute:

For changes that have a corresponding issue:

.. code-block:: sh

    towncrier create <issue>.<type>.rst --edit

For changes that have no corresponding issue:

.. code-block:: sh

    towncrier create noissue.<number>.<type>.rst --edit

For changes where you do not want to create or modify a change log entry,
simply don't provide a change fragment file.

where:

* ``<issue>`` - The issue number of the issue that is addressed by the change.
  If the change addresses more than one issue, copy the new change fragment file
  after its content has been edited, using the other issue number in the file
  name. It is important that the file content is exactly the same, so that
  towncrier can create a single change log entry from the two (or more) files.

  If the change has no related issue, use the ``noissue.<number>.<type>.rst``
  file name format, where ``<number>`` is any number that results in a file name
  that does not yet exist in the ``changes`` directory.

* ``<type>`` - The type of the change, using one of the following values:

  - ``incompatible`` - An incompatible change. This will show up in the
    "Incompatible Changes" section of the change log. The text should include
    a description of the incompatibility from a user perspective and if
    possible, how to mitigate the change or what replacement functionality
    can be used instead.

  - ``deprecation`` - An externally visible functionality is being deprecated
    in this release.
    This will show up in the "Deprecations" section of the change log.
    The deprecated functionality still works in this release, but may go away
    in a future release. If there is a replacement functionality, the text
    should mention it.

  - ``fix`` - A bug fix in the code, documentation or development environment.
    This will show up in the "Bug fixes" section of the change log.

  - ``feature`` - A feature or enhancement in the code, documentation or
    development environment.
    This will show up in the "Enhancements" section of the change log.

  - ``cleanup`` - A cleanup in the code, documentation or development
    environment, that does not fix a bug and is not an enhanced functionality.
    This will show up in the "Cleanup" section of the change log.

This command will create a new change fragment file in the ``changes``
directory and will bring up your editor (usually vim).

If your change does multiple things of different types listed above, create
a separate change fragment file for each type.

If you need to modify an existing change log entry as part of your change,
edit the existing corresponding change fragment file.

Add the new or changed change fragment file(s) to your commit. The test
workflow running on your Pull Request will check whether your change adds or
modifies change fragment files.

You can review how your changes will show up in the final change log for
the upcoming release by running:

.. code-block:: sh

    towncrier build --draft

Always make sure that your pushed branch has either just one commit, or if you
do multiple things, one commit for each logical change. What is not OK is to
keep the possibly multiple commits it took you to get to the final result for
the change.

Format of commit messages
-------------------------

A commit message must start with a short summary line, followed by a blank line.

Optionally, the summary line may start with an identifier that helps identifying
the type of change or the component that is affected, followed by a colon.

It can include a more detailed description after the summary line. This is where
you explain why the change was done, and summarize what was done.

It must end with the DCO (Developer Certificate of Origin) sign-off line in the
format shown in the example below, using your name and a valid email address of
yours. The DCO sign-off line certifies that you followed the rules stated in
`DCO 1.1`_. In short, you certify that you wrote the patch or otherwise have the
right to pass it on as an open-source patch.

.. _DCO 1.1: https://developercertificate.org/

We use `GitCop`_ during creation of a pull request to check whether the commit
messages in the pull request comply to this format. If the commit messages do
not comply, GitCop will add a comment to the pull request with a description of
what was wrong.

.. _GitCop: http://gitcop.com/

Example commit message:

.. code-block:: text

    cookies: Add support for delivering cookies

    Cookies are important for many people. This change adds a pluggable API for
    delivering cookies to the user, and provides a default implementation.

    Signed-off-by: Random J Developer <random@developer.org>

Use ``git commit --amend`` to edit the commit message, if you need to.

Use the ``--signoff`` (``-s``) option of ``git commit`` to append a sign-off
line to the commit message with your name and email as known by Git.

If you like filling out the commit message in an editor instead of using the
``-m`` option of ``git commit``, you can automate the presence of the sign-off
line by using a commit template file:

* Create a file outside of the repo (say, ``~/.git-signoff.template``)
  that contains, for example:

  .. code-block:: text

      <one-line subject>

      <detailed description>

      Signed-off-by: Random J Developer <random@developer.org>

* Configure Git to use that file as a commit template for your repo:

  .. code-block:: text

      git config commit.template ~/.git-signoff.template

Releasing a version
-------------------

This section shows the steps for releasing a version to `PyPI`_.

.. _PyPI: https://pypi.python.org/

It covers all variants of versions that can be released:

* Releasing a new major version (Mnew.0.0) based on the master branch
* Releasing a new minor version (M.Nnew.0) based on the master branch or based
  on an earlier stable branch
* Releasing a new update version (M.N.Unew) based on the stable branch of its
  minor version

This description assumes that you are authorized to push to the remote repo
at https://github.com/zhmcclient/zhmc-prometheus-exporter and that the remote repo
has the remote name ``origin`` in your local clone.

Any commands in the following steps are executed in the main directory of your
local clone of the zhmc-prometheus-exporter Git repo.

1.  On GitHub, verify open items in milestone ``M.N.U``.

    Verify that milestone ``M.N.U`` has no open issues or PRs anymore. If there
    are open PRs or open issues, make a decision for each of those whether or
    not it should go into version ``M.N.U`` you are about to release.

    If there are open issues or PRs that should go into this version, abandon
    the release process.

    If none of the open issues or PRs should go into this version, change their
    milestones to a future version, and proceed with the release process. You
    may need to create the milestone for the future version.

2.  Run the Safety tool:

    .. code-block:: sh

        make safety

    If any of the two safety runs fails, fix the safety issues that are reported,
    in a separate branch/PR.

    Roll back the PR into any maintained stable branches.

3.  Check for any
    `dependabot alerts <https://github.com/zhmcclient/zhmc-prometheus-exporter/security/dependabot>`_.

    If there are any dependabot alerts, fix them in a separate branch/PR.

    Roll back the PR into any maintained stable branches.

4.  Create and push the release branch (replace M,N,U accordingly):

    .. code-block:: sh

        VERSION=M.N.U make release_branch

    This uses the default branch determined from ``VERSION``: For ``M.N.0``,
    the ``master`` branch is used, otherwise the ``stable_M.N`` branch is used.
    That covers for all cases except if you want to release a new minor version
    based on an earlier stable branch. In that case, you need to specify that
    branch:

    .. code-block:: sh

        VERSION=M.N.0 BRANCH=stable_M.N make release_branch

    This includes the following steps:

    * create the release branch (``release_M.N.U``), if not yet existing
    * make sure the AUTHORS.md file is up to date
    * update the change log from the change fragment files, and delete those
    * commit the changes to the release branch
    * push the release branch

    If this command fails, the fix can be committed to the release branch
    and the command above can be retried.

5.  On GitHub, create a Pull Request for branch ``release_M.N.U``.

    Important: When creating Pull Requests, GitHub by default targets the
    ``master`` branch. When releasing based on a stable branch, you need to
    change the target branch of the Pull Request to ``stable_M.N``.

    Set the milestone of that PR to version ``M.N.U``.

    This PR should normally be set to be reviewed by at least one of the
    maintainers.

    The PR creation will cause the "test" workflow to run. That workflow runs
    tests for all defined environments, since it discovers by the branch name
    that this is a PR for a release.

6.  On GitHub, once the checks for that Pull Request have succeeded, merge the
    Pull Request (no review is needed). This automatically deletes the branch
    on GitHub.

    If the PR did not succeed, fix the issues.

7.  On GitHub, close milestone ``M.N.U``.

    Verify that the milestone has no open items anymore. If it does have open
    items, investigate why and fix (probably step 1 was not performed).

8.  Publish the package (replace M,N,U accordingly):

    .. code-block:: sh

        VERSION=M.N.U make release_publish

    or (see step 4):

    .. code-block:: sh

        VERSION=M.N.0 BRANCH=stable_M.N make release_publish

    This includes the following steps:

    * create and push the release tag
    * clean up the release branch

    Pushing the release tag will cause the "publish" workflow to run. That workflow
    builds the package, publishes it on PyPI, creates a release for it on
    GitHub, and finally creates a new stable branch on GitHub if the master
    branch was released.

9.  Verify the publishing

    Wait for the "publish" workflow for the new release to have completed:
    https://github.com/zhmcclient/zhmc-prometheus-exporter/actions/workflows/publish.yml

    Then, perform the following verifications:

    * Verify that the new version is available on PyPI at
      https://pypi.python.org/pypi/zhmc-prometheus-exporter/

    * Verify that the new version has a release on Github at
      https://github.com/zhmcclient/zhmc-prometheus-exporter/releases

    * Verify that the new version has documentation on ReadTheDocs at
      https://zhmc-prometheus-exporter.readthedocs.io/en/latest/changes.html

      The new version ``M.N.U`` should be automatically active on ReadTheDocs,
      causing the documentation for the new version to be automatically
      built and published.

      If you cannot see the new version after some minutes, log in to
      https://readthedocs.org/projects/zhmc-prometheus-exporter/versions/
      and activate the new version.


Starting a new version
----------------------

This section shows the steps for starting development of a new version.

This section covers all variants of new versions:

* Starting a new major version (Mnew.0.0) based on the master branch
* Starting a new minor version (M.Nnew.0) based on the master branch
* Starting a new update version (M.N.Unew) based on the stable branch of its
  minor version

This description assumes that you are authorized to push to the remote repo
at https://github.com/zhmcclient/zhmc-prometheus-exporter and that the remote repo
has the remote name ``origin`` in your local clone.

Any commands in the following steps are executed in the main directory of your
local clone of the zhmc-prometheus-exporter Git repo.

1.  Create and push the start branch (replace M,N,U accordingly):

    .. code-block:: sh

        VERSION=M.N.U make start_branch

    This uses the default branch determined from ``VERSION``: For ``M.N.0``,
    the ``master`` branch is used, otherwise the ``stable_M.N`` branch is used.
    That covers for all cases except if you want to start a new minor version
    based on an earlier stable branch. In that case, you need to specify that
    branch:

    .. code-block:: sh

        VERSION=M.N.0 BRANCH=stable_M.N make start_branch

    This includes the following steps:

    * create the start branch (``start_M.N.U``), if not yet existing
    * create a dummy change
    * commit and push the start branch (``start_M.N.U``)

2.  On GitHub, create a milestone for the new version ``M.N.U``.

    You can create a milestone in GitHub via Issues -> Milestones -> New
    Milestone.

3.  On GitHub, create a Pull Request for branch ``start_M.N.U``.

    Important: When creating Pull Requests, GitHub by default targets the
    ``master`` branch. When starting a version based on a stable branch, you
    need to change the target branch of the Pull Request to ``stable_M.N``.

    No review is needed for this PR.

    Set the milestone of that PR to the new version ``M.N.U``.

4.  On GitHub, go through all open issues and pull requests that still have
    milestones for previous releases set, and either set them to the new
    milestone, or to have no milestone.

    Note that when the release process has been performed as described, there
    should not be any such issues or pull requests anymore. So this step here
    is just an additional safeguard.

5.  On GitHub, once the checks for the Pull Request for branch ``start_M.N.U``
    have succeeded, merge the Pull Request (no review is needed). This
    automatically deletes the branch on GitHub.

6.  Update and clean up the local repo (replace M,N,U accordingly):

    .. code-block:: sh

        VERSION=M.N.U make start_tag

    or (see step 1):

    .. code-block:: sh

        VERSION=M.N.0 BRANCH=stable_M.N make start_tag

    This includes the following steps:

    * checkout and pull the branch that was started (``master`` or ``stable_M.N``)
    * delete the start branch (``start_M.N.U``) locally and remotely
    * create and push the start tag (``M.N.Ua0``)

Building the distribution archives
----------------------------------

You can build a binary (wheel) distribution archive and a source distribution
archive (a more minimal version of the repository) with:

.. code-block:: bash

  $ make build

You will find the files ``zhmc_prometheus_exporter-VERSION_NUMBER-py3-none-any.whl``
and ``zhmc_prometheus_exporter-VERSION_NUMBER.tar.gz`` in the ``dist`` folder,
the former being the binary and the latter being the source distribution archive.

The binary distribution archive could be installed with:

.. code-block:: bash

  $ pip install zhmc_prometheus_exporter-VERSION_NUMBER-py3-none-any.whl

The source distribution archive could be installed with:

.. code-block:: bash

  $ tar -xfz zhmc_prometheus_exporter-VERSION_NUMBER.tar.gz
  $ pip install zhmc_prometheus_exporter-VERSION_NUMBER

Building the documentation
--------------------------

You can build the HTML documentation with:

.. code-block:: bash

  $ make builddoc

The root file for the built documentation will be ``build_docs/index.html``.

Testing
-------

You can perform unit tests with:

.. code-block:: bash

  $ make test

The environment variables ``TESTCASES`` and ``TESTOPTS`` can be specified for
unit tests. Invoke ``make help`` for details.

You can perform a flake8 check with:

.. code-block:: bash

  $ make check

You can perform a pylint check with:

.. code-block:: bash

  $ make pylint

Format of metric definition file
--------------------------------

The metric definition file is in YAML format and has the following structure:

.. code-block:: yaml

    metric_groups:
      # dictionary of metric groups:
      {hmc-metric-group}:
        prefix: {resource-type}
        if: {fetch-condition}  # optional
        labels:
          # list of labels to be added to all metrics of this group:
          - name: {label-name}
            value: {label-value}

    metrics:
      # dictionary of metric groups:
      {hmc-metric-group}:

        # dictionary format for defining metrics:
        {hmc-metric}:
          if: {export-condition}  # optional
          exporter_name: {exporter-name}
          exporter_desc: {exporter-desc}
          metric_type: {metric-type}
          percent: {percent-bool}
          valuemap: {valuemap}
          labels:
            # list of labels to be added to this metric:
            - name: {label-name}
              value: {label-value}

        # list format for defining metrics:
        - property_name: {hmc-metric}                     # either this
          properties_expression: {properties-expression}  # or this
          if: {export-condition}  # optional
          exporter_name: {exporter-name}
          exporter_desc: {exporter-desc}
          percent: {percent-bool}
          valuemap: {valuemap}
          labels:
            # list of labels to be added to this metric:
            - name: {label-name}
              value: {label-value}

    fetch_properties:
      # dictionary of properties that need to be fetched because they can
      # change but have no property change notification
      {hmc-resource-class}:
        - property_name: {hmc-property}
          if: {fetch-condition}  # optional

Where:

* ``{hmc-metric-group}`` is the name of the metric group on the HMC.

* ``{hmc-metric}`` is the name of the metric (within the metric group) on the
  HMC.

* ``{resource-type}`` is a short lower case term for the type of resource
  the metric applies to, for example ``cpc`` or ``partition``. It is used
  in the Prometheus metric name directly after the initial ``zhmc_``.

* ``{fetch-condition}`` is a string that is evaluated as a Python expression and
  that indicates whether the metric group can be fetched. For the metric group
  to actually be fetched, the ``fetch`` property also needs to be True.
  The expression may use the following variables; builtins are not available:

  - ``hmc_version`` - HMC version as a tuple of integers (M, N, U), e.g.
    (2, 16, 0).
  - ``hmc_api_version`` - HMC API version as a tuple of integers (M, N), e.g.
    (4, 10).
  - ``hmc_features`` - List of names of HMC API features. Will be empty before
    HMC API version 4.10.

* ``{properties-expression}`` is a :term:`Jinja2 expression` whose value should
  be used as the metric value, for :term:`resource property based metrics`. The
  expression uses the variable ``properties`` which is the resource properties
  dictionary of the resource. The ``properties_expression`` attribute is
  mutually exclusive with ``property_name``.

* ``{export-condition}`` is a string that is evaluated as a Python expression
  and that controls whether the metric is exported. If it evaluates to false,
  the export of the metric is disabled, regardless of other such controls.
  The expression may use the following variables; builtins are not available:

  - ``hmc_version`` - HMC version as a tuple of integers (M, N, U), e.g.
    (2, 16, 0).
  - ``hmc_api_version`` - HMC API version as a tuple of integers (M, N), e.g.
    (4, 10).
  - ``hmc_features`` - List of names of HMC API features. Will be empty before
    HMC API version 4.10.
  - ``se_version`` - SE/CPC version as a tuple of integers (M, N, U), e.g.
    (2, 16, 0). Will be `None` when there is no CPC context for the metric.
  - ``se_features`` - List of names of SE/CPC API features. Will be an empty
    list before HMC API version 4.10 or before SE version 2.16.0 or when there
    is no CPC context for the metric.
  - ``resource_obj`` - zhmcclient resource object for the metric.

* ``{exporter-name}`` is the local metric name and unit in the exported metric
  name ``zhmc_{resource-type}_{exporter-name}``.
  If it is null, the export of the metric is disabled, regardless of other such
  controls.

* ``{exporter-desc}`` is the description text that is exported as ``# HELP``.

* ``{metric-type}`` is an optional enum value that defines the Prometheus metric
  type used for this metric:
  - "gauge" (default) - For values that can go up and down
  - "counter" - For values that are monotonically increasing counters

* ``{percent-bool}`` is a boolean indicating whether the metric value should
  be divided by 100. The reason for this is that the HMC metrics represent
  percentages such that a value of 100 means 100% = 1, while Prometheus
  represents them such that a value of 1.0 means 100% = 1.

* ``{valuemap}`` is an optional dictionary for mapping string enumeration values
  in the original HMC value to integers to be exported to Prometheus. This is
  used for example for the processor mode (shared, dedicated).

* ``{label-name}`` is the label name.

* ``{label-value}`` is a :term:`Jinja2 expression` that is evaluated and used
  as the label value. For details, see :ref:`Labels on exported metrics`.

* ``{hmc-resource-class}`` is the class of the HMC resource for which properties
  are to be fetched (i.e. the value of its ``class`` property, e.g. ``cpc``).

* ``{hmc-property}`` is the HMC name of the property that is to be fetched.
