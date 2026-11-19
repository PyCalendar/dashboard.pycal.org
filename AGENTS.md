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
- Every class and function has a docstring in the Google style, whose section of the
  arguments is `Parameters:`, never `Args:`; every argument has a type. `make lint` and
  `tests/quality/test_docstrings.py` check it.
- The tests never use the network: GitHub is faked (`tests/fakes/github.py`).
- Never change a migration that may be applied somewhere; add a new one.
- No inline JavaScript in templates; small static scripts in `static/` may enhance a
  page. Every page works without JavaScript.
- All pages are public, except those based on private information: the
  account, the preferences, the email addresses, the webhook deliveries and
  private projects. A private repository is only in private projects and only
  their people see it; it is added only through the GitHub App installed on it,
  by a person who may read it (`RepositoryLookup`). Who may do what in a project
  is decided in one place, `ProjectAccess`.
- The privacy policy (`pycal_dashboard/privacy.py`, the page `/about/privacy/`)
  always says which data of people the site keeps and who gets it: change it
  with every change of what the site keeps or sends. `tests/test_privacy.py`
  fails for a model or field it does not list.
- Nothing is loaded from other sites: no fonts (such as Google Fonts), scripts
  or styles. Only the avatars of GitHub (`EXTERNAL_HOSTS` of the privacy
  policy); `tests/test_privacy.py` checks the files and the pages.
- Texts that people type to describe something are Markdown: shown with `|markdown`
  (`markdown_text.py`, cleaned by nh3) and edited with the partial `_markdown_field.html` (a bar
  of formats and a preview). `tests/test_markdown.py` checks the templates.
- People of GitHub are shown with `{% github_user %}` (`templatetags/github.py`):
  their avatar from GitHub before their name, linked to GitHub.
- A page with public JSON goes into `pycal_dashboard/json_api.py`, which makes `/llms.txt` (the
  guideline for agents) and `/robots.txt`, and into `docs/reference/json.rst`;
  `tests/test_agents.py` checks that the guideline is complete and every address answers.
- The conditions of pull requests are in `pycal_dashboard/conditions/`: `condition/` (on
  `base.py`), `input/` (the kinds of inputs, which also make the fields of forms) and `spec/`
  (the data the background reads and whether it is complete). Each condition has its id, its
  own page `docs/reference/conditions/<id>.rst` with the API reference at its bottom, and is in
  `CONDITIONS`; `tests/test_conditions.py` checks them. Data whose permissions the GitHub App
  does not ask for is described but not read: asking for a permission is the person's decision.
- Every model is registered in the Django admin (`pycal_dashboard/admin.py`),
  which the people of `SITE_ADMINS` reach; `tests/test_account.py` checks it.
- Of GitHub, the site keeps the installations of the GitHub App with their
  permissions (`Installation`), the repositories of the projects with what
  it read of them (`Repository`), all their issues and pull requests (`Issue`)
  and the accounts that created them (`GitHubUser`, linked to the `User` who
  signs in with it). When what it keeps of GitHub changes, raise `DATA_VERSION`
  (`pycal_dashboard/github/data_version.py`) with the migration: the
  repositories are read completely again in the background after it.
- Every update takes the same path, whoever starts it (the button, a webhook, the hourly
  routine, a page that may be out of date): `UpdateQueue` -> `RepositoryUpdate` in the
  background -> the signals of `update_signals.py`. What follows an update is a receiver in
  `receivers.py`, never code of one trigger. `tests/test_update_paths.py` checks it. It reads GitHub in the background only
  (`UpdateQueue`, run by `UpdateWorker`), never while a page waits, except to
  find what a person adds. It writes nothing to GitHub yet; the app may write
  labels and a comment on pull requests for the automation, designed later.
- Every flow of people (signing in, creating a project, ...) has a browser test
  in `tests/browser/`. The browser reaches nothing but the site.
- Every setting that can be set is in `.env.example`, with its description (a `##` line
  directly above it) and its default, in the sections of the file; and in
  `docs/reference/settings.rst`. `tests/test_settings.py` checks both.
- New permissions or events of the GitHub App go into
  `pycal_dashboard/github/permissions.py` and `docs/reference/permissions.rst`, and their
  names for people into `pycal_dashboard/github/permission_names.py`: as GitHub names and
  describes them on the page of the permissions of an app, whose text is
  `pycal_dashboard/github/permission_names.txt` (the reference; `tests/test_permission_names.py`
  compares them). People see the names of GitHub, never those of the API.

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

## Translations

- Texts are marked for translation and extracted (`make messages`), but translated only when the
  person asks: ask before translating. Until then a text shows in English. `make messages`
  guesses no translations (no fuzzy matching).

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
