================================
``label_exists``: A label exists
================================

A label exists on a pull request.

Holds when the pull request has the label of the input ``label``, such as
``needs review``; its case does not matter.

It is checked on pull requests only. While the data of a pull request is not
complete, the condition cannot be assessed yet.

Inputs
======

.. list-table::
   :header-rows: 1

   * - Name
     - Type
     - Required
     - What it is
   * - ``label``
     - ``string-label``
     - yes
     - The name of a label of the repository.

The type ``string-label`` is the name of a label of the repository: the
configuration is refused with
:class:`~pycal_dashboard.errors.conditions.ConditionLabelUnknown` for a name
the repository does not have; its case does not matter.

The inputs as JSON:

.. code-block:: json

   {"label": "needs review"}

Data
====

The update of the repository reads in the background:

``labels``
   The labels of the repository and of the pull request. Permissions of the
   GitHub App: ``metadata``: read, ``issues``: read; webhooks: ``issues``,
   ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.label_exists.LabelExists
   :members: assess
   :show-inheritance:
