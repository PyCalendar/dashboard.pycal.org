==========
Conditions
==========

A condition is checked on a pull request, such as whether it has a label. Each
has an id, the inputs that configure it, and the data that the update of the
repository reads for it in the background. The conditions are not shown on the
pages yet.

.. list-table::
   :header-rows: 1

   * - Id
     - What it checks
   * - :doc:`label_exists`
     - A label exists on a pull request.
   * - :doc:`label_absent`
     - A label is absent from a pull request.
   * - :doc:`ci_passes`
     - The checks of the last commit of a pull request passed.
   * - :doc:`ci_fails`
     - A check of the last commit of a pull request failed.
   * - :doc:`merge_conflict`
     - A pull request has a merge conflict with its base branch.
   * - :doc:`branch_outdated`
     - The branch of a pull request is behind its base branch.
   * - :doc:`auto_merge_enabled`
     - Auto-merge is enabled on a pull request.
   * - :doc:`open`
     - A pull request is open.
   * - :doc:`merged`
     - A pull request was merged.
   * - :doc:`closed`
     - A pull request was closed without being merged.

.. toctree::
   :hidden:

   label_exists
   label_absent
   ci_passes
   ci_fails
   merge_conflict
   branch_outdated
   auto_merge_enabled
   open
   merged
   closed
   api

Inputs
======

The types of the inputs, which also make the field of a form that asks for them
(:meth:`~pycal_dashboard.conditions.input.base.InputSpec.widget`, shown by the
partial ``conditions/_input.html``):

``string``
   A text.
``int``
   A whole number, with an optional smallest and largest number.
``positive-int``
   A whole number from 1 up.
``range``
   Two whole numbers, ``[low, high]``, low not above high.
``string-label``
   The name of a label of the repository.

Data
====

The data of a pull request that conditions need, with the permissions and
webhooks of the GitHub App that reading it needs. The state of the open pull
requests comes with one query of GraphQL for each repository, made of the
fields that every kind of data needs: about one point of GitHub for 50 pull
requests, where the REST API needs requests for each one. GraphQL needs a
token, so it reads only repositories with the GitHub App, and only the fields
whose permissions the owners of the installation accepted: the checks wait
until they accept ``checks`` and ``statuses``. When GitHub gives up on a slow
query (502), the site asks for the same page with half as many pull requests. Data whose permissions the
app does not ask for is not read.

``issue``
   Whether the pull request is open, closed or merged.
``labels``
   The labels of the repository and of the pull request.
``pull_request``
   Whether the pull request can be merged, is behind its base, and merges itself.
``checks``
   The checks and statuses of the last commit of the pull request.

See :doc:`api` for the classes.
