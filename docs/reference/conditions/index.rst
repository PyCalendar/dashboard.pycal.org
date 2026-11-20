==========
Conditions
==========

A condition is checked on a pull request, such as whether it has a label. Each
has an id, the inputs that configure it, and the data that the update of the
repository reads for it in the background. A condition is a state of a pull
request that is true or false; the :doc:`states of people </reference/states/index>`
are numbers, and conditions such as ``review_ratio_above`` check them.

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
   * - :doc:`ci_unknown`
     - The result of the checks of a pull request is not known.
   * - :doc:`merge_conflict`
     - A pull request has a merge conflict with its base branch.
   * - :doc:`branch_outdated`
     - The branch of a pull request is behind its base branch.
   * - :doc:`branch_up_to_date`
     - The branch of a pull request is up to date with its base branch.
   * - :doc:`auto_merge_enabled`
     - Auto-merge is enabled on a pull request.
   * - :doc:`open`
     - A pull request is open.
   * - :doc:`merged`
     - A pull request was merged.
   * - :doc:`closed`
     - A pull request was closed without being merged.
   * - :doc:`reviews_at_least`
     - A pull request has at least a number of reviews, without those of
       comments.
   * - :doc:`review_ratio_above`
     - The review to pull request ratio of the author is above a number.

.. toctree::
   :hidden:

   label_exists
   label_absent
   ci_passes
   ci_fails
   ci_unknown
   merge_conflict
   branch_outdated
   branch_up_to_date
   auto_merge_enabled
   open
   merged
   closed
   reviews_at_least
   review_ratio_above
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
``number``
   A number, also with a fraction, such as ``1.5``.
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
``reviews``
   The reviews of all pull requests of the repository, open and closed, and
   who closed each. One query of GraphQL reads 20 pull requests, the last
   changed first, and stops at those it read before; the first 100 reviews of
   a pull request are read.

See :doc:`api` for the classes.
