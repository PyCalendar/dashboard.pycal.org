==========
Conditions
==========

A condition is checked on a pull request, such as whether it has a label. Each
has an id, the inputs that configure it, and the data that the update of the
repository reads for it in the background. A condition is a state of a pull
request that is true or false; the :doc:`states of people </reference/states/index>`
are numbers, and conditions such as ``review_ratio`` compare them with a number.

Each condition shows its evidence on the page of a pull request: the least that
shows why it holds or not, such as the checks on GitHub, or as many reviews as
decide it (:class:`~pycal_dashboard.conditions.evidence.Evidence`). The data
specs give the links of their data, which the conditions reuse
(:meth:`~pycal_dashboard.conditions.spec.base.DataSpec.evidence`), and a
condition chooses the least of them
(:meth:`~pycal_dashboard.conditions.condition.base.Condition.evidence`).

Every condition can be inverted: its NOT
(:class:`~pycal_dashboard.conditions.condition.negation.Not`, made by
:meth:`~pycal_dashboard.conditions.condition.base.Condition.negate`) is wrapped
around it and holds exactly when it does not; while the condition is not known,
neither is its NOT. The NOT has its own id, title and description, and the
inputs, the data and the evidence of the condition; the NOT of a NOT is the
condition again. ``label_absent`` is the NOT of ``label_exists``.

A condition is made of its class and a creation spec, the inputs by name, such
as ``LabelExists({"label": "bug"})``, and yields the same spec again
(:meth:`~pycal_dashboard.conditions.condition.base.Condition.spec`). How
conditions are written down and read again is not their business, but that of
the factory of the conditions
(:class:`~pycal_dashboard.conditions.factory.ConditionFactory`): it makes a
condition of its class or id and a spec, writes it as a spec with its id, such
as ``{"id": "label_absent", "label": "bug"}``, and as the choices of a column
of the table of pull requests, such as ``labels~applies~absent~bug``. Each
group of columns says only which specs its choices mean, and which choices
write specs. So a NOT and the condition that it is are the same: the choices
``absent`` and the NOT of ``present`` (``not~labels~applies~present~bug``)
read as the same condition, written as ``absent``; the NOT of *at least 2
reviews* is written as *below 2*. A NOT that its group has no choices for is
written as the NOT of the condition, with ``not~``. The switches of a column
that are on are joined by OR
(:class:`~pycal_dashboard.conditions.condition.any_of.AnyOf`): one of them
holds.

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
   * - :doc:`draft`
     - A pull request is a draft: not ready for review yet.
   * - :doc:`merged`
     - A pull request was merged.
   * - :doc:`closed`
     - A pull request was closed without being merged.
   * - :doc:`reviews`
     - A pull request has a number of reviews, without those of comments only.
   * - :doc:`review_ratio`
     - The review to pull request ratio of the author compared with a number.
   * - :doc:`author_state`
     - A state of the author of a pull request compared with a number.
   * - :doc:`author_type`
     - The author of a pull request is an owner, a member, a collaborator, ...
   * - :doc:`text_matches`
     - The title or the description of a pull request matches a text or a regex.
   * - :doc:`pr_sync`
     - The PR Sync of the project is on for a pull request: it has its Status Message.
   * - :doc:`step_skipped`
     - A pull request skips a step of the project, skipped by a person or for its author.

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
   draft
   merged
   closed
   reviews
   review_ratio
   author_state
   author_type
   text_matches
   pr_sync
   step_skipped
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
``comparison``
   How a number is compared: ``above``, ``below``, ``at_most``, ``at_least``
   or ``exactly``; at most and at least include the number.
``range``
   Two whole numbers, ``[low, high]``, low not above high.
``string-label``
   The name of a label of the repository.
``bool``
   On or off: ``true`` or ``false``; a switch in a form.
``choice``
   One of a few names, such as ``title`` or ``description``.
``review-kinds``
   The kinds of reviews that count, of ``approved``, ``changes_requested``,
   ``commented`` and ``dismissed``; all of them by default; and ``own``, the
   reviews of the author of a pull request on it, which do not count by
   default. A switch for each in a form. Every condition and state that counts
   reviews has it as ``kinds``.

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
