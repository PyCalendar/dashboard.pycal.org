======================================================
``own_pull_requests_closed``: Own pull requests closed
======================================================

How many pull requests a person opened and closed themselves in the project.

Such as a pull request withdrawn, or opened by mistake. Who closed a pull
request is read with the reviews: those closed by others, or merged, do not
count.

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
``reviews``
   The reviews of the pull requests and who closed them. Permissions of the
   GitHub App: ``pull_requests``: read; webhooks: ``pull_request_review``,
   ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.state.own_pull_requests_closed.OwnPullRequestsClosed
   :members: measure
   :show-inheritance:
