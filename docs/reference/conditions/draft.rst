================
``draft``: Draft
================

A pull request is a draft: not ready for review yet.

Holds while the author marked the pull request as a draft on GitHub, as GitHub
tells with each pull request; a draft is open, too. The column *Status* has it
as the switch *draft*, such as ``status~applies~draft``; inverted, it shows the
pull requests that are ready for review.

It is checked on pull requests only. Until the repository was read again
completely after dashboard.pycal.org kept the drafts (data version 5), the
condition cannot be assessed yet.

Inputs
======

The condition has no inputs.

Data
====

The update of the repository reads in the background:

``issue``
   The pull request, with whether it is a draft. Permissions of the GitHub
   App: ``pull_requests``: read; webhooks: ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.draft.Draft
   :members: assess, complete
   :show-inheritance:
