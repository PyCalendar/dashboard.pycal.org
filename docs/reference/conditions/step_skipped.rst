================================
``step_skipped``: A step skipped
================================

A pull request skips a step of the project, skipped by a person or for its author.

Holds when a writer of the project skipped one of its steps for the pull request, or when
a step skips itself for the author of the pull request, see :ref:`pull-request-page`. The
column *Dashboard* has it as the switch *a skipped step*.

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

.. autoclass:: pycal_dashboard.conditions.condition.step_skipped.StepSkipped
   :members: assess
   :show-inheritance:
