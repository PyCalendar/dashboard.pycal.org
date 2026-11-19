==================================
``merge_conflict``: Merge conflict
==================================

A pull request has a merge conflict with its base branch.

Holds when GitHub says that the pull request cannot be merged into its base
branch because they changed the same lines (``mergeable_state`` is ``dirty``).

It is checked on pull requests only. While the data of a pull request is not
complete, the condition cannot be assessed yet.

Inputs
======

The condition has no inputs.

Data
====

The update of the repository reads in the background:

``pull_request``
   Whether the pull request can be merged, is behind its base, and merges
   itself. Permissions of the GitHub App: ``pull_requests``: read; webhooks:
   ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.merge_conflict.MergeConflict
   :members: assess
   :show-inheritance:
