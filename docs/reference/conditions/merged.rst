==================
``merged``: Merged
==================

A pull request was merged.

Holds when the pull request was merged into its base branch.

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

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.merged.Merged
   :members: assess
   :show-inheritance:
