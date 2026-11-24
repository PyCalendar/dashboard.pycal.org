=====================
``reviews``: Reviews
=====================

A pull request has a number of reviews, of the kinds that count: all by default, but not those of its author.

Holds when the number of reviews of the pull request compares with the input
``reviews`` as the input ``comparison`` says, such as at least 2. The input
``kinds`` says which reviews count, the switches *Which reviews count* of the
column: approved, changes requested, commented and dismissed, all of them by
default. By default, a review counts only when its author is not the author of
the pull request, such as a comment of the author as a review; ``own``, the
switch *by the author of the pull request*, counts those, too. A dismissed review is an approval or a request for changes that a
maintainer dismissed later, such as after new commits. The same input is in the
states :doc:`/reference/states/reviews_given` and
:doc:`/reference/states/review_ratio` and the condition :doc:`review_ratio`.

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
   * - ``kinds``
     - ``review-kinds``
     - no, all of them
     - The kinds of reviews that count: ``approved``, ``changes_requested``,
       ``commented`` and ``dismissed``.

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

   {"comparison": "at_least", "reviews": 2, "kinds": ["approved", "changes_requested"]}

In the address of the table, a column that counts some kinds only ends with
them, such as ``reviews~applies~at_least~2~approved~changes_requested``; without
kinds, all of them count. A column saved with ``~comments`` before counts all of
them.

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
