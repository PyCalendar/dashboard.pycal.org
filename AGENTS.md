# Rules for AI agents

These rules are for AI agents (Claude Code and others) that change this
repository. People who use AI follow the [AI policy of icalendar and the Python
Calendaring Ecosystem](https://icalendar.readthedocs.io/en/latest/contribute/index.html).

## Prompts and todos

- The prompts are recorded in `.prompts/` by the hook of
  [ai-prompt-auto-commit](https://github.com/PyCalendar/ai-prompt-auto-commit)
  (`.claude/settings.json`). Do not edit or delete them.
- Every prompt becomes items of `todo.txt` (markdown checkboxes), which is
  committed. Mark items `- [x]` when they are done and tested. Decisions that
  belong to the person (names, accounts, releases) stay open items.

## Commits

- The person has given standing authorization, for this repository only, to
  commit and push finished work, with the migrations it needs. Commit, push,
  check that the branch matches the remote and that the CI run of the push
  passes; fix it if not.
- Ask before deleting or overwriting outside the files the agent made.
- Commits written by an agent end with the attribution of the model.

## Constraints of the code

- One class per module; a module that would need more becomes a package. The
  errors are the exception: they are grouped by topic in
  `pycal_dashboard/errors/`. `tests/quality/test_structure.py` checks this.
- Errors are split up as finely as possible: one class per cause, with a title
  and a docstring that says what happened and how to solve it. They are shown
  with a link to their documentation (`docs/reference/errors.rst`).
- Every class and function has a docstring in the Google style; `make lint`
  checks it.
- The tests never use the network: GitHub is faked (`tests/fakes/github.py`).
- Never change a migration that may be applied somewhere; add a new one.
- No inline JavaScript in templates; small static scripts in `static/` may enhance a
  page. Every page works without JavaScript.
- All pages are public, except those based on private information: the
  account, the preferences, the email addresses and the webhook deliveries.
  Private repositories are never shown.
- Every model is registered in the Django admin (`pycal_dashboard/admin.py`),
  which the people of `SITE_ADMINS` reach; `tests/test_account.py` checks it.
- The site keeps no data of GitHub for now (no models that track or query the
  GitHub API) and writes nothing to GitHub; numbers and automation are separate
  functionality, designed later. The one exception: the installations of the
  GitHub App with their permissions (`Installation`), so that people are told
  when an installation needs more.
- Every setting that can be set is in `.env.example`, with its description (a `##` line
  directly above it) and its default, in the sections of the file; and in
  `docs/reference/settings.rst`. `tests/test_settings.py` checks both.
- New permissions or events of the GitHub App go into
  `pycal_dashboard/github/permissions.py` and `docs/reference/permissions.rst`.

- The idle memory of the service stays as low as possible: one process of nginx and of gunicorn
  by default, and the packages that are only needed now and then (GitHub, JWT, the licenses) are
  imported where they are used, not at the top of the modules that the pages load.
  `tests/quality/test_memory.py` checks that the pages of every day load none of them; measure
  the container (`docker stats`) when a change adds a dependency or a process.
- Every lazy import (an import inside a function) goes through the import guard,
  `with IMPORT_GUARD:` of `pycal_dashboard/import_guard.py`, as in community-insights: threads
  that import at the same time could otherwise stop each other in a deadlock.
  `tests/quality/test_lazy_imports.py` checks every import and imports in threads at once.

## Tests

- Every change comes with tests, also of the errors people can see.
- Run `make lint`, `make test`, `make browser-test` and `make docs` and report
  the results as they are.

## Changelog and documentation

- Every change people notice has a news fragment in `news/`, named without `.rst`, such as
  `news/+topic.feature` or `news/12.bugfix`. The documentation shows them in the changelog:
  `docs/conf.py` drafts them with towncrier at each build.
- The documentation (`docs/`) is updated with the change.

<!-- ai-prompt-auto-commit: start -->
## AI prompt recording

At the start of a session, read [.github/assistant-guidelines.md](.github/assistant-guidelines.md).
Follow its instructions for reminding contributors to activate prompt-recording
hooks and for storing prompts without duplicates.
<!-- ai-prompt-auto-commit: end -->
