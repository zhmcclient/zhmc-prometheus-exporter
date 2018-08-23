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

The exporter is on `GitHub`_.

.. _GitHub: https://github.com/zhmcclient/zhmc-prometheus-exporter

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

What comprises a "logical" change is subject to sound judgement. Sometimes, it makes sense to produce a set of commits for a feature (even if not large). For example, a first commit may introduce a (presumably) compatible API change without exploitation of that feature. With only this commit applied, it should be demonstrable that everything is still working as before. The next commit may be the exploitation of the feature in other components.

For further discussion of good and bad practices regarding commits, see:

* `OpenStack Git Commit Good Practice`_
* `How to Get Your Change Into the Linux Kernel`_

.. _OpenStack Git Commit Good Practice: https://wiki.openstack.org/wiki/GitCommitMessages
.. _How to Get Your Change Into the Linux Kernel: https://www.kernel.org/doc/Documentation/SubmittingPatches

Format of commit messages
-------------------------

A commit message must start with a short summary line, followed by a blank line.

Optionally, the summary line may start with an identifier that helps identifying the type of change or the component that is affected, followed by a colon.

It can include a more detailed description after the summary line. This is where you explain why the change was done, and summarize what was done.

It must end with the DCO (Developer Certificate of Origin) sign-off line in the format shown in the example below, using your name and a valid email address of yours. The DCO sign-off line certifies that you followed the rules stated in `DCO 1.1`_. In short, you certify that you wrote the patch or otherwise have the right to pass it on as an open-source patch.

.. _DCO 1.1: https://developercertificate.org/

We use `GitCop`_ during creation of a pull request to check whether the commit messages in the pull request comply to this format. If the commit messages do not comply, GitCop will add a comment to the pull request with a description of what was wrong.

.. _GitCop: http://gitcop.com/

Example commit message:

.. code-block:: text

    cookies: Add support for delivering cookies

    Cookies are important for many people. This change adds a pluggable API for
    delivering cookies to the user, and provides a default implementation.

    Signed-off-by: Random J Developer <random@developer.org>

Use ``git commit --amend`` to edit the commit message, if you need to.

Use the ``--signoff`` (``-s``) option of ``git commit`` to append a sign-off line to the commit message with your name and email as known by Git.

If you like filling out the commit message in an editor instead of using the ``-m`` option of ``git commit``, you can automate the presence of the sign-off line by using a commit template file:

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

Switch to your work directory of the python-zhmcclient Git repo (this is where the ``Makefile`` is), and perform the following steps in that directory:

1.  Set a shell variable for the version to be released, e.g.:

    .. code-block:: bash

        $ MNU='0.11.0'

2.  Verify that your working directory is in a Git-wise clean state:

    .. code-block:: bash

        $ git status

3.  Check out the ``master`` branch, and update it from upstream:

    .. code-block:: bash

        $ git checkout master
        $ git pull

4.  Create a topic branch for the release, based upon the ``master`` branch:

    .. code-block:: bash

        git checkout -b release-$MNU

5.  Edit the change log (``docs/changes.rst``) and perform the following changes in the top-most section (that is the section for the version to be released):

    * If needed, change the version in the section heading to the version to be released, e.g.:

      .. code-block:: text

          Version 0.11.0
          ^^^^^^^^^^^^^^

    * Change the release date to today's date, e.g.:

      .. code-block:: text

          Released: 2018-08-20

    * Make sure that the change log entries reflect all changes since the previous version, and make sure they are relevant for and understandable by users.

    * In the "Known issues" list item, remove the link to the issue tracker and add any known issues you want users to know about. Just linking to the issue tracker quickly becomes incorrect for released versions:

      .. code-block:: text

          **Known issues:**

          * ...

    * Remove all empty list items in the change log section for this release.

6.  Commit your changes and push them upstream:

    .. code-block:: bash

        $ git add docs/changes.rst
        $ git commit -sm "Updated change log for $MNU release."
        $ git push --set-upstream origin release-$MNU

7.  On GitHub, create a pull request for branch ``release-$MNU``.

8.  Perform a complete test:

    .. code-block:: bash

        $ make test

    This should not fail because the same tests have already been run in the Travis CI. However, run it for additional safety before the release.

    * If this test fails, fix any issues until the test succeeds. Commit the changes and push them upstream:

      .. code-block:: bash

          $ git add <changed-files>
          $ git commit -sm "<change description with details>"
          $ git push

      Wait for the automatic tests to show success for this change.

9.  Once the CI tests on GitHub are complete, merge the pull request.

10. Update your local ``master`` branch:

    .. code-block:: bash

        $ git checkout master
        $ git pull

11. Tag the ``master`` branch with the release label and push the tag upstream:

    .. code-block:: bash

        $ git tag $MNU
        $ git push --tags

12. On GitHub, edit the new tag, and create a release description on it. This will cause it to appear in the Release tab.

    You can see the tags in GitHub via Code -> Releases -> Tags.

13. Upload the package to PyPI:

    .. code-block:: bash

        $ make upload

    This will show the package version and will ask for confirmation.

    **Attention!** This only works once for each version. You cannot release the same version twice to PyPI.

14. Verify that the released version is shown on PyPI.

15. On GitHub, close milestone ``M.N.U``.

Build a package
---------------

You can build a binary and a source distribution with

.. code-block:: bash

  $ make build

You will find the files ``zhmc_prometheus_exporter-VERSION_NUMBER-py2.py3-none-any.whl`` and ``zhmc_prometheus_exporter-VERSION_NUMBER.tar.gz`` in the ``dist`` folder, the former being the binary and the latter being the source distribution.

The binary could then be installed with

.. code-block:: bash

  $ pip3 install zhmc_prometheus_exporter-VERSION_NUMBER-py2.py3-none-any.whl 

The source distribution (a more minimal version of the repository) can be unpacked with

.. code-block:: bash

  $ tar xfz zhmc_prometheus_exporter-VERSION_NUMBER.tar.gz

Build the documentation
-----------------------

You can build the documentation as HTML with

.. code-block:: bash

  $ make builddoc

The root for the built documentation will be ``docs/_build/index.html``.

Unit & lint testing
-------------------

You can perform unit tests based on ``unittest`` with

.. code-block:: bash

  $ make test

If you want to speed up test time, you can remove the timeout test.

You can perform lint tests based on ``flake8`` with

.. code-block:: bash

  $ make lint

Cleanup processes
-----------------

The package can be uninstalled with

.. code-block:: bash

  $ make uninstall

The unnecessary files from the build process can be removed with

.. code-block:: bash

  $ make clean
