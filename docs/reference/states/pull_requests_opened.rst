==============================================
``pull_requests_opened``: Pull requests opened
==============================================

How many pull requests a person opened in the project.

All of them count: open, merged and closed. Observed on a pull request, its
author is counted, with this pull request.

It is observed on a person in a project: the author of a pull request, or a
person of GitHub, counted in all repositories of the project that the viewer
sees. While the data of a repository of the project is not complete, it is not
known yet.

Inputs
======

The state has no inputs.

Data
====

The update of the repository reads in the background:

``issue``
   Whether the pull request is open, closed or merged. Permissions of the
   GitHub App: ``pull_requests``: read; webhooks: ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.state.pull_requests_opened.PullRequestsOpened
   :members: measure
   :show-inheritance:
