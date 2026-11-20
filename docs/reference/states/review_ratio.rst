==============================================
``review_ratio``: Review to pull request ratio
==============================================

The reviews a person gave in the project for each pull request they opened and
did not close themselves.

It is ``reviews_given / (pull_requests_opened - own_pull_requests_closed)``,
made of those states. Without such pull requests, it is infinite with reviews,
and 0 without. The condition :doc:`/reference/conditions/review_ratio`
checks it.

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

.. autoclass:: pycal_dashboard.conditions.state.review_ratio.ReviewRatio
   :members: measure
   :show-inheritance:
