========================================
``branch_up_to_date``: Branch up to date
========================================

The branch of a pull request is up to date with its base branch.

Holds when the pull request is neither behind its base branch nor has a
conflict with it; a merged pull request is up to date, too.

It is checked on pull requests only. While the data of a pull request is not
complete, the condition cannot be assessed yet.

Inputs
======

The condition has no inputs.

Data
====

The update of the repository reads in the background:

``issue``
   Whether the pull request is open, closed or merged. Permissions of the
   GitHub App: ``pull_requests``: read; webhooks: ``pull_request``.
``pull_request``
   Whether the pull request can be merged, is behind its base, and merges
   itself. Permissions of the GitHub App: ``pull_requests``: read,
   ``contents``: read; webhooks: ``pull_request``, ``push``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.branch_up_to_date.BranchUpToDate
   :members: assess
   :show-inheritance:
