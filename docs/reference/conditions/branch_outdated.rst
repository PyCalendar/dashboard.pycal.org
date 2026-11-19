=======================================
``branch_outdated``: Branch out of date
=======================================

The branch of a pull request is behind its base branch.

Holds when its base branch has commits that the branch of the pull request does
not have, and the repository requires branches to be up to date before merging
(``mergeable_state`` is ``behind``). A merged pull request is not out of date.

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
   itself. Permissions of the GitHub App: ``pull_requests``: read,
   ``contents``: read; webhooks: ``pull_request``, ``push``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.branch_outdated.BranchOutdated
   :members: assess
   :show-inheritance:
