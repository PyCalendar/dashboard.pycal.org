======================================================
``reviews_at_least``: At least a number of reviews
======================================================

A pull request has at least a number of reviews, without those of comments.

Holds when the pull request has at least as many reviews as the input
``reviews``. A review counts when it approved, requested changes, or was
dismissed later; a review with comments only does not count.

It is checked on pull requests only. While the data of a pull request is not
complete, the condition cannot be assessed yet.

Inputs
======

.. list-table::
   :header-rows: 1

   * - Name
     - Type
     - Required
     - What it is
   * - ``reviews``
     - ``positive-int``
     - yes
     - The fewest reviews it has.

The inputs as JSON:

.. code-block:: json

   {"reviews": 2}

Data
====

The update of the repository reads in the background:

``reviews``
   The reviews of the pull requests and who closed them. Permissions of the
   GitHub App: ``pull_requests``: read; webhooks: ``pull_request_review``,
   ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.reviews_at_least.ReviewsAtLeast
   :members: assess
   :show-inheritance:
