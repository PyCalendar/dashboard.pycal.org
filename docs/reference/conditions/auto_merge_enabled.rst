==========================================
``auto_merge_enabled``: Auto-merge enabled
==========================================

Auto-merge is enabled on a pull request.

Holds when someone enabled auto-merge: GitHub merges the pull request as soon
as its requirements, such as reviews and checks, are met.

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

.. autoclass:: pycal_dashboard.conditions.condition.auto_merge_enabled.AutoMergeEnabled
   :members: assess
   :show-inheritance:
