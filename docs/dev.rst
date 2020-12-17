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
* Releasing a new minor version (M.Nnew.0) based on the master branch
* Releasing a new update version (M.N.Unew) based on the stable branch of its
  minor version

This description assumes that you are authorized to push to the remote repo
at https://github.com/zhmcclient/zhmc-ansible-modules and that the remote repo
has the remote name ``origin`` in your local clone.

Any commands in the following steps are executed in the main directory of your
local clone of the zhmc-ansible-modules Git repo.

1.  Set shell variables for the version that is being released and the branch
    it is based on:

    * ``MNU`` - Full version M.N.U that is being released
    * ``MN`` - Major and minor version M.N of that full version
    * ``BRANCH`` - Name of the branch the version that is being released is
      based on

    When releasing a new major version (e.g. ``1.0.0``) based on the master
    branch:

    .. code-block:: sh

        MNU=1.0.0
        MN=1.0
        BRANCH=master

    When releasing a new minor version (e.g. ``0.9.0``) based on the master
    branch:

    .. code-block:: sh

        MNU=0.9.0
        MN=0.9
        BRANCH=master

    When releasing a new update version (e.g. ``0.8.1``) based on the stable
    branch of its minor version:

    .. code-block:: sh

        MNU=0.8.1
        MN=0.8
        BRANCH=stable_${MN}

2.  When releasing based on the master branch, create and push a new stable
    branch for the same minor version:

    .. code-block:: sh

        git checkout master
        git pull
        git checkout -b stable_${MN}
        git push --set-upstream origin stable_${MN}

    Note that no GitHub Pull Request is created for any ``stable_*`` branch.

3.  Create a topic branch for the version that is being released:

    .. code-block:: sh

        git checkout ${BRANCH}
        git pull
        git checkout -b release_${MNU}

4.  Edit the version file:

    .. code-block:: sh

        vi zhmc_prometheus_exporter/_version.py

    and set the ``__version__`` variable to the version that is being released:

    .. code-block:: python

        __version__ = 'M.N.U'

5.  Edit the change log:

    .. code-block:: sh

        vi docs/changes.rst

    and make the following changes in the section of the version that is being
    released:

    * Finalize the version.
    * Change the release date to today's date.
    * Make sure that all changes are described.
    * Make sure the items shown in the change log are relevant for and
      understandable by users.
    * In the "Known issues" list item, remove the link to the issue tracker and
      add text for any known issues you want users to know about.
    * Remove all empty list items.

6.  When releasing based on the master branch, edit the GitHub workflow file
    ``test.yml``:

    .. code-block:: sh

        vi .github/workflows/test.yml

    and in the ``on`` section, increase the version of the ``stable_*`` branch
    to the new stable branch ``stable_M.N`` created earlier:

    .. code-block:: yaml

        on:
          schedule:
            . . .
          push:
            branches: [ master, stable_M.N ]
          pull_request:
            branches: [ master, stable_M.N ]

7.  Commit your changes and push the topic branch to the remote repo:

    .. code-block:: sh

        git status  # Double check the changed files
        git commit -asm "Release ${MNU}"
        git push --set-upstream origin release_${MNU}

8.  On GitHub, create a Pull Request for branch ``release_M.N.U``. This will
    trigger the CI runs.

    Important: When creating Pull Requests, GitHub by default targets the
    ``master`` branch. When releasing based on a stable branch, you need to
    change the target branch of the Pull Request to ``stable_M.N``.

9.  On GitHub, close milestone ``M.N.U``.

10. Perform a complete test in your preferred Python environment:

    .. code-block:: sh

        make test

    This should not fail because the same tests have already been run in the
    CI. However, run it for additional safety before the release.

    If this test fails, fix any issues (with new commits) until the test
    succeeds.

11. On GitHub, once the checks for the Pull Request for branch ``start_M.N.U``
    have succeeded, merge the Pull Request (no review is needed). This
    automatically deletes the branch on GitHub.

    This also triggers a build of the documentation on ReadTheDocs.
    Verify that the released version is shown on ReadTheDocs at
    https://zhmc-prometheus-exporter.readthedocs.io/

12. Add a new tag for the version that is being released and push it to
    the remote repo. Clean up the local repo:

    .. code-block:: sh

        git checkout ${BRANCH}
        git pull
        git tag -f ${MNU}
        git push -f --tags
        git branch -d release_${MNU}

13. On GitHub, edit the new tag ``M.N.U``, and create a release description on
    it. This will cause it to appear in the Release tab.

    You can see the tags in GitHub via Code -> Releases -> Tags.

14. Upload the package to PyPI:

    .. code-block:: sh

        make upload

    This will show the package version and will ask for confirmation.

    **Attention!** This only works once for each version. You cannot release
    the same version twice to PyPI.

    Verify that the released version arrived on PyPI at
    https://pypi.python.org/pypi/zhmc-prometheus-exporter/

Starting a new version
----------------------

This section shows the steps for starting development of a new version.

This section covers all variants of new versions:

* Starting a new major version (Mnew.0.0) based on the master branch
* Starting a new minor version (M.Nnew.0) based on the master branch
* Starting a new update version (M.N.Unew) based on the stable branch of its
  minor version

This description assumes that you are authorized to push to the remote repo
at https://github.com/zhmcclient/zhmc-ansible-modules and that the remote repo
has the remote name ``origin`` in your local clone.

Any commands in the following steps are executed in the main directory of your
local clone of the zhmc-ansible-modules Git repo.

1.  Set shell variables for the version that is being started and the branch it
    is based on:

    * ``MNU`` - Full version M.N.U that is being started
    * ``MN`` - Major and minor version M.N of that full version
    * ``BRANCH`` -  Name of the branch the version that is being started is
      based on

    When starting a new major version (e.g. ``1.0.0``) based on the master
    branch:

    .. code-block:: sh

        MNU=1.0.0
        MN=1.0
        BRANCH=master

    When starting a new minor version (e.g. ``0.9.0``) based on the master
    branch:

    .. code-block:: sh

        MNU=0.9.0
        MN=0.9
        BRANCH=master

    When starting a new minor version (e.g. ``0.8.1``) based on the stable
    branch of its minor version:

    .. code-block:: sh

        MNU=0.8.1
        MN=0.8
        BRANCH=stable_${MN}

2.  Create a topic branch for the version that is being started:

    .. code-block:: sh

        git checkout ${BRANCH}
        git pull
        git checkout -b start_${MNU}

3.  Edit the version file:

    .. code-block:: sh

        vi zhmc_prometheus_exporter/_version.py

    and update the version to a draft version of the version that is being
    started:

    .. code-block:: python

        __version__ = 'M.N.U.dev1'

4.  Edit the change log:

    .. code-block:: sh

        vi docs/changes.rst

    and insert the following section before the top-most section:

    .. code-block:: rst

        Version M.N.U.dev1
        ^^^^^^^^^^^^^^^^^^

        This version contains all fixes up to version M.N-1.x.

        Released: not yet

        **Incompatible changes:**

        **Deprecations:**

        **Bug fixes:**

        **Enhancements:**

        **Cleanup:**

        **Known issues:**

        * See `list of open issues`_.

        .. _`list of open issues`: https://github.com/zhmcclient/zhmc-prometheus-exporter/issues

5.  Commit your changes and push them to the remote repo:

    .. code-block:: sh

        git status  # Double check the changed files
        git commit -asm "Start ${MNU}"
        git push --set-upstream origin start_${MNU}

6.  On GitHub, create a Pull Request for branch ``start_M.N.U``.

    Important: When creating Pull Requests, GitHub by default targets the
    ``master`` branch. When starting a version based on a stable branch, you
    need to change the target branch of the Pull Request to ``stable_M.N``.

7.  On GitHub, create a milestone for the new version ``M.N.U``.

    You can create a milestone in GitHub via Issues -> Milestones -> New
    Milestone.

8.  On GitHub, go through all open issues and pull requests that still have
    milestones for previous releases set, and either set them to the new
    milestone, or to have no milestone.

9.  On GitHub, once the checks for the Pull Request for branch ``start_M.N.U``
    have succeeded, merge the Pull Request (no review is needed). This
    automatically deletes the branch on GitHub.

10. Update and clean up the local repo:

    .. code-block:: sh

        git checkout ${BRANCH}
        git pull
        git branch -d start_${MNU}

Building the distribution archives
----------------------------------

You can build a binary (wheel) distribution archive and a source distribution
archive (a more minimal version of the repository) with:

.. code-block:: bash

  $ make build

You will find the files ``zhmc_prometheus_exporter-VERSION_NUMBER-py2.py3-none-any.whl``
and ``zhmc_prometheus_exporter-VERSION_NUMBER.tar.gz`` in the ``dist`` folder,
the former being the binary and the latter being the source distribution archive.

The binary distribution archive could be installed with:

.. code-block:: bash

  $ pip install zhmc_prometheus_exporter-VERSION_NUMBER-py2.py3-none-any.whl

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

You can perform a flake8 check with:

.. code-block:: bash

  $ make check

You can perform a pylint check with:

.. code-block:: bash

  $ make pylint
