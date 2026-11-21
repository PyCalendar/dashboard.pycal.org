==================================================
``review_ratio``: Review to pull request ratio
==================================================

The review to pull request ratio of the author compared with a number.

Holds when the state :doc:`/reference/states/review_ratio` of the author of the
pull request, counted in all repositories of the project, compares with the
input ``ratio`` as the input ``comparison`` says, such as below 1: the author
gave fewer reviews than they opened pull requests that others had to look at.
The ratio is

.. code-block:: text

   reviews_given / (pull_requests_opened - own_pull_requests_closed)

of the states :doc:`/reference/states/reviews_given`,
:doc:`/reference/states/pull_requests_opened` and
:doc:`/reference/states/own_pull_requests_closed`. For example:

- ``1``: as many reviews as pull requests,
- ``0.5``: half as many reviews as pull requests,
- ``2``: twice as many reviews as pull requests.

It is checked on pull requests only. While the data of a repository of the
project is not complete, the condition cannot be assessed yet.

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
     - no, ``above``
     - How the ratio compares with the number: ``above``, ``below``,
       ``at_most``, ``at_least`` or ``exactly``, see :doc:`reviews`; at most
       and at least include the number.
   * - ``ratio``
     - ``number``
     - yes
     - The reviews given for each pull request opened and not closed by the
       author.
   * - ``kinds``
     - ``review-kinds``
     - no, all of them
     - The kinds of reviews that count: ``approved``, ``changes_requested``,
       ``commented`` and ``dismissed``.

The input ``kinds`` comes from the state :doc:`/reference/states/review_ratio`,
which has it from :doc:`/reference/states/reviews_given`: the inputs of a state
travel to the conditions and states that use it.

The type ``number`` is a number with a point before a fraction, from 0 up.

The inputs as JSON:

.. code-block:: json

   {"comparison": "below", "ratio": 1}

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

.. autoclass:: pycal_dashboard.conditions.condition.review_ratio.ReviewRatioCompared
   :members: assess
   :show-inheritance:
