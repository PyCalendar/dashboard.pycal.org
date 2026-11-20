=====================
``reviews``: Reviews
=====================

A pull request has a number of reviews, without those of comments only.

Holds when the number of reviews of the pull request compares with the input
``reviews`` as the input ``comparison`` says, such as at least 2. A review
counts when it approved, requested changes, or was dismissed later; a review
with comments only does not count.

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
   * - ``comparison``
     - ``comparison``
     - no, ``at_least``
     - How the reviews compare with the number.
   * - ``reviews``
     - ``int``
     - yes
     - The number of reviews to compare with, from 0 up.

The type ``comparison`` is one of these; *at most* and *at least* include the
number itself:

.. list-table::
   :header-rows: 1

   * - Value
     - Reads
     - Holds when the number of reviews is
   * - ``above``
     - more than >
     - larger than the number
   * - ``below``
     - fewer than <
     - smaller than the number
   * - ``at_most``
     - at most ≤
     - the number or smaller
   * - ``at_least``
     - at least ≥
     - the number or larger
   * - ``exactly``
     - exactly =
     - the number

The inputs as JSON:

.. code-block:: json

   {"comparison": "at_least", "reviews": 2}

Data
====

The update of the repository reads in the background:

``reviews``
   The reviews of the pull requests and who closed them. Permissions of the
   GitHub App: ``pull_requests``: read; webhooks: ``pull_request_review``,
   ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.reviews.Reviews
   :members: assess
   :show-inheritance:
