=======================
``pr_sync``: PR Sync on
=======================

The PR Sync of the project is on for a pull request: it has its Status Message.

Holds when the GitHub App wrote the Status Message of the project as a comment on the pull
request, because it is in the scope of the message, see :ref:`pr-message`. The column
*Dashboard* has it as the switch *PR Sync on*.

It is data of the dashboard, not of GitHub: it is known for the pull requests of a project,
and its results are not kept in the cache, as they change without an update from GitHub.

Inputs
======

The condition has no inputs.

Data
====

``dashboard``
   What the dashboard keeps of a pull request: its PR Sync and the skips of its steps.
   Nothing is read from GitHub for it, and it needs no permission of the GitHub App.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.pr_sync_on.PrSyncOn
   :members: assess
   :show-inheritance:
