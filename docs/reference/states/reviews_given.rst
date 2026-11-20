================================
``reviews_given``: Reviews given
================================

How many reviews a person gave in the project, without those of comments only.

A review counts when it approved, requested changes, or was dismissed later; a
review with comments only does not count.

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

``reviews``
   The reviews of the pull requests and who closed them. Permissions of the
   GitHub App: ``pull_requests``: read; webhooks: ``pull_request_review``,
   ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.state.reviews_given.ReviewsGiven
   :members: measure
   :show-inheritance:
