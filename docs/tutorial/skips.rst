.. _skips:

=================================
Skip steps and quality checks
=================================

A pull request goes through the steps of its project, see :ref:`project-steps`.
It is in the left-most step with a quality check to do. Sometimes a step or a
quality check does not fit a pull request, such as a review that the
maintainers did at a meeting, or a changelog entry for a change of a typo.
Then a person skips it, and says why.

What a skip does
================

A skipped step
   The pull request is in the next step that shows it. The skipped step is gray,
   with a dashed border, and it still shows its quality checks; its actions do
   not follow, see :ref:`status-labels`.

A skipped quality check
   It keeps the pull request in its step no more, as if it was done. When every
   quality check of a step is done or skipped, the step is complete and the pull
   request goes on to the next step. The badge counts a skipped quality check as
   done, such as *Review 2/2*. The quality check shows ⏩ on the page of the pull
   request, and in the PR message ``:fast_forward:``, which GitHub shows as ⏩,
   where a quality check done has ✔️ and one to do ❌, see :ref:`pr-message`.

Everybody who sees the pull request sees what is skipped and who skipped it,
linked to their page in the project. Only the writers and owners of the project
see why. **Don't skip** next to it undoes a skip; only the writers and owners
see it.

Who skips
=========

- The writers and owners of the project skip every step and every quality check
  of a pull request, with **Skip** on the page of the pull request, see
  :ref:`pull-request-page` and :ref:`project-roles`.
- The author of a pull request skips a step or a quality check when the project
  gives them its link with a key: the variables that end in ``_author``, see
  below. Nobody but dashboard.pycal.org can make the key, so the author skips
  only what the project offers them.

Besides, a step skips itself for some pull requests, and then names nobody:
those its conditions *Skip if* apply to, and those of the authors named in
*Skipped for these authors*, see :ref:`project-steps`.

The reason
==========

Each skip needs a reason. The dialog of **Skip** asks why the step or the
quality check can be skipped, such as *Why can the quality check Update the
changelog be skipped?*. ✕ closes the dialog. The reason is Markdown, with a bar
of formats and a preview: **bold**, *italic*, links and lists. It has no
variables: a name in braces, such as ``{pr_title}``, stays as it is.

Links to skip
=============

The summary of a step, the summaries and descriptions of its quality checks and
the PR message take four variables of the group *Skip*, see
:ref:`step-variables`. Each is the address of the page of the pull request on
dashboard.pycal.org, with the step shown and the dialog to skip open.

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Variable
     - Skips
     - Who may skip
   * - ``{step_check_skip_url}``
     - The step
     - The writers and owners
   * - ``{step_check_skip_url_author}``
     - The step
     - The writers and owners, and the author of the pull request
   * - ``{quality_check_skip_url}``
     - The quality check whose text has it
     - The writers and owners
   * - ``{quality_check_skip_url_author}``
     - The quality check whose text has it
     - The writers and owners, and the author of the pull request

The variables of quality checks are for the summaries and descriptions of
quality checks: they skip that quality check. Such as the description of the
quality check *Update the changelog*:

.. code-block:: markdown

   Add a news fragment to `news/`. When your change needs none, such as for a
   typo, [skip this quality check]({quality_check_skip_url_author}).

What the link does depends on who opens it:

- A writer or owner of the project, or the author with a link of the author,
  sees the dialog as with **Skip**: they write the reason and skip.
- A visitor who did not sign in sees the dialog with **Sign in with GitHub** in
  place of the button that skips. They write the reason and sign in. Back on the
  page, the skip is made as if they had clicked the button, when they may skip
  it.
- Who may not skip it sees the dialog with the error
  :class:`~pycal_dashboard.errors.projects.SkipNotAllowed` and the reason that
  they typed, such as a person who signed in with another account of GitHub than
  that of the author.

A link opens no dialog when there is nothing to skip: a step that the pull
request skips already, or a quality check that is done or skipped.
dashboard.pycal.org keeps the reason in the session, which the cookie
``sessionid`` names, only until they are back, as its privacy policy says
(``/about/privacy/``).
