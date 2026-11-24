================================
``reviews_given``: Reviews given
================================

How many reviews a person gave in the project, of the kinds that count: all by default, but not those on the pull requests of the person.

The input ``kinds`` says which reviews count: approved, changes requested,
commented and dismissed, all of them by default. A review on a pull request of
the person counts only with ``own``, the switch *by the author of the pull
request*. A dismissed review is an
approval or a request for changes that a maintainer dismissed later, such as
after new commits.

It is observed on a person in a project: the author of a pull request, or a
person of GitHub, counted in all repositories of the project that the viewer
sees. While the data of a repository of the project is not complete, it is not
known yet.

Inputs
======

.. list-table::
   :header-rows: 1

   * - Name
     - Type
     - Required
     - What it is
   * - ``kinds``
     - ``review-kinds``
     - no, all of them
     - The kinds of reviews that count: ``approved``, ``changes_requested``,
       ``commented`` and ``dismissed``.

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
