========================
``ci_passes``: CI passes
========================

The checks of the last commit of a pull request passed.

Holds when every check run and commit status of its last commit succeeded, or
was skipped or neutral; also when it has none. While checks run, the last
complete result counts.

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
``checks``
   The checks and statuses of the last commit of the pull request.
   Permissions of the GitHub App: ``checks``: read, ``statuses``: read;
   webhooks: ``check_run``, ``check_suite``, ``status``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.ci_passes.CiPasses
   :members: assess
   :show-inheritance:
