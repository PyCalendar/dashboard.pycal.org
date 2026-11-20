==============================================================
``review_ratio_above``: Review to pull request ratio above
==============================================================

The review to pull request ratio of the author is above a number.

Holds when the state :doc:`/reference/states/review_ratio` of the author of the
pull request, counted in all repositories of the project, is above the input
``ratio``, such as ``1.5``: the author gave more than one and a half reviews
for each pull request of theirs. The ratio is

.. code-block:: text

   reviews_given / (pull_requests_opened - own_pull_requests_closed)

of the states :doc:`/reference/states/reviews_given`,
:doc:`/reference/states/pull_requests_opened` and
:doc:`/reference/states/own_pull_requests_closed`.

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
   * - ``ratio``
     - ``number``
     - yes
     - The reviews given for each pull request opened and not closed by the
       author.

The type ``number`` is a number with a point before a fraction, from 0 up.

The inputs as JSON:

.. code-block:: json

   {"ratio": 1.5}

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

.. autoclass:: pycal_dashboard.conditions.condition.review_ratio_above.ReviewRatioAbove
   :members: assess
   :show-inheritance:
