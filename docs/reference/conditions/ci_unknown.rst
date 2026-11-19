==========================
``ci_unknown``: CI unknown
==========================

The result of the checks of a pull request is not known.

Holds when neither ``ci_passes`` nor ``ci_fails`` can be assessed: the site has
not read the checks of its last commit, such as for a closed pull request or
while the GitHub App may not read checks and statuses, or its checks never
completed. Exactly one of ``ci_passes``, ``ci_fails`` and ``ci_unknown`` holds
for every pull request.

It is checked on pull requests only.

Inputs
======

The condition has no inputs.

Data
====

It needs no data but the pull request, and holds while the data of
:doc:`ci_passes` is not complete.

``issue``
   Whether the pull request is open, closed or merged. Permissions of the
   GitHub App: ``pull_requests``: read; webhooks: ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.ci_unknown.CiUnknown
   :members: assess
   :show-inheritance:
