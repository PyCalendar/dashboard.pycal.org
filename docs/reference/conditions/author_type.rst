===============================
``author_type``: Type of author
===============================

The author of a pull request is an owner, a member, a collaborator, ...

Holds when the type of the author is one of the input ``types``. GitHub tells
the association of the author with the repository with each pull request, its
``author_association``; the types group the associations:

.. list-table::
   :header-rows: 1

   * - Type
     - Who it is
     - Associations of GitHub
   * - ``owner``
     - The owner of the repository.
     - ``OWNER``
   * - ``member``
     - A member of the organization of the repository.
     - ``MEMBER``
   * - ``collaborator``
     - A collaborator who was invited to the repository.
     - ``COLLABORATOR``
   * - ``contributor``
     - A contributor whose contributions were merged before; also an account
       imported from another platform, a mannequin.
     - ``CONTRIBUTOR``, ``MANNEQUIN``
   * - ``first_timer``
     - A first-timer: the pull request is the first contribution of the author,
       to the repository or to GitHub, or there is none yet.
     - ``FIRST_TIME_CONTRIBUTOR``, ``FIRST_TIMER``, ``NONE``

The types are exclusive: an author has exactly one type for a pull request,
the most privileged that GitHub found, so a member of the organization is not a
contributor, too. Inverting a column of some types therefore chooses the other
types. The type is that of the pull request: a first-timer becomes a
contributor on the next pull request after the first is merged. Bots are not a
type of their own; they have the association of their account.

The column *Type of author* has it, with a switch for each type; its cell
shows the type of the author.

It is checked on pull requests only. Until the repository was read again
completely after dashboard.pycal.org kept the association (data version 4), the condition
cannot be assessed yet.

Inputs
======

.. list-table::
   :header-rows: 1

   * - Name
     - Type
     - Required
     - What it is
   * - ``types``
     - ``choices``
     - yes
     - Some of ``owner``, ``member``, ``collaborator``, ``contributor`` and
       ``first_timer``.

The inputs as JSON:

.. code-block:: json

   {"types": ["contributor", "first_timer"]}

In the address of the table, such as ``author_type~applies~first_timer``.

Data
====

The update of the repository reads in the background:

``issue``
   The pull request with the association of its author. Permissions of the
   GitHub App: ``pull_requests``: read; webhooks: ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.author_type.AuthorType
   :members: assess, complete
   :show-inheritance:
