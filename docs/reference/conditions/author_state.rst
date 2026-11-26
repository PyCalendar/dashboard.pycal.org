==========================================
``author_state``: A state of the author
==========================================

A state of the author of a pull request compared with a number.

Holds when the state of the input ``state`` of the author of the pull request,
counted in all repositories of the project, compares with the input ``number``
as the input ``comparison`` says, such as below 2. The states are those of
people:

- :doc:`/reference/states/review_ratio`: the reviews given for each pull
  request opened and not closed by the author,
- :doc:`/reference/states/reviews_given`: the reviews that the author gave,
- :doc:`/reference/states/pull_requests_opened`: the pull requests that the
  author opened,
- :doc:`/reference/states/own_pull_requests_closed`: the pull requests that the
  author opened and closed without a merge.

The input ``kinds`` says which reviews count, for a state that counts reviews.
The column *Author* of the table of pull requests checks it, such as
``author~applies~reviews_given~below~2``; its NOT is written with the opposite
comparison, such as ``at_least`` for ``below``.

It is checked on pull requests only. Without an author, or while the data of a
repository of the project that the state needs is not complete, the condition
cannot be assessed yet.

Inputs
======

.. list-table::
   :header-rows: 1

   * - Name
     - Type
     - Required
     - What it is
   * - ``state``
     - ``choice``
     - yes
     - ``review_ratio``, ``reviews_given``, ``pull_requests_opened`` or
       ``own_pull_requests_closed``.
   * - ``comparison``
     - ``comparison``
     - no, ``below``
     - How the state compares with the number: ``above``, ``below``,
       ``at_most``, ``at_least`` or ``exactly``; at most and at least include
       the number.
   * - ``number``
     - ``number``
     - yes
     - The number to compare the state with, from 0 up.
   * - ``kinds``
     - ``review-kinds``
     - no, all of them
     - The kinds of reviews that count, for ``review_ratio`` and
       ``reviews_given``: ``approved``, ``changes_requested``, ``commented``
       and ``dismissed``.

The inputs as JSON:

.. code-block:: json

   {"state": "reviews_given", "comparison": "below", "number": 2}

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

.. autoclass:: pycal_dashboard.conditions.condition.author_state.AuthorState
   :members: check, evidence
   :show-inheritance:
