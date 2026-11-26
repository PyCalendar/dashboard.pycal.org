# Rules for AI agents

These rules are for every AI agent that changes this repository: Claude Code, Codex and
others, for whoever on the team runs them. People who use AI follow the [AI policy of
icalendar and the Python Calendaring
Ecosystem](https://icalendar.readthedocs.io/en/latest/contribute/index.html). The rules of the
code below are checked by the tests: when a test of `tests/quality/` or `tests/test_*.py` fails
after a change, follow the rule it names instead of changing the test.

## Start here

- Set up a clone with `make dev` (Python with uv, the packages, the git hooks, the recording of
  prompts, the database), and once `make browser-install` for the browser tests. `make help`
  lists every target. [docs/how-to/develop.rst](docs/how-to/develop.rst) explains the setup,
  the settings for development (`cp .env.development.example .env`) and the models.
- The checks, which the CI runs, too:

  | Command | What it checks |
  | --- | --- |
  | `make lint` | ruff: the style, the imports and the Google docstrings |
  | `make test` | the unit and API tests, in parallel, with coverage; missing migrations |
  | `make browser-test` | the flows of people in Chromium (Playwright) |
  | `make docs` | the documentation; every warning fails |
  | `make prose` | the prose of the documentation (Vale) |

  One test: `uv run pytest tests/test_steps.py -k visible`. `JOBS=0 make test` runs in one
  process, which shows a failure more clearly. In a shell, use `set -o pipefail` when the
  output of a check goes through `tail` or `grep`, so that a failure is not hidden.
- `make messages` extracts the texts to translate and compiles them; it uses gettext, or Docker
  without it. `make migrations` makes the migrations of changed models.
- Where the code is:

  | Path | What it holds |
  | --- | --- |
  | `pycal_dashboard/views/` | the pages, one module per area (`projects.py`, `steps.py`, ...) |
  | `pycal_dashboard/services/` | the logic of the site: one class per module |
  | `pycal_dashboard/conditions/` | the conditions of pull requests, see below |
  | `pycal_dashboard/models/` | the models, one per module |
  | `pycal_dashboard/errors/` | the errors that people see, grouped by topic |
  | `pycal_dashboard/templates/`, `static/` | the HTML and the small scripts and styles |
  | `tests/fakes/github.py` | the fake GitHub of all tests |
  | `docs/` | the documentation: tutorial, how-to, reference, explanation |
  | `todo.txt` | the requirements of the prompts and what is open |

## Working for a person

- You work for the person who runs you. Decisions that belong to people stay theirs: names,
  accounts, permissions of the GitHub App, releases, translations, and whether to change live
  data. Ask about them, or leave them as open items in `todo.txt`.
- Ask questions that only the person can answer at the end of the work, not in between, and
  do the rest meanwhile.
- Ask before deleting or overwriting files that you did not make. Files of the person that are
  not part of the repository, such as notes or downloaded pages in the root of the clone, are
  never committed: add them by name.
- Secrets are never committed nor printed: `.env`, tokens such as a `*-token.txt` in the root
  of a clone, and keys. Before each commit, check the names of the staged files. The tests
  need no secret.
- The live site, <https://dashboard.pycal.org>, is used read-only: its pages, its public JSON
  (`/llms.txt` lists them) and logs that the person gives you access to. Do not change data on
  it, and ask before anything that could disturb it, such as load or reproducing an error.

## Prompts and todos

- The prompts are recorded in `.prompts/` by the hooks of
  [ai-prompt-auto-commit](https://github.com/PyCalendar/ai-prompt-auto-commit)
  (`.claude/settings.json` for Claude Code, `.codex/hooks.json` for Codex). Do not edit or
  delete them; see *AI prompt recording* at the bottom.
- Every prompt becomes items of `todo.txt` (markdown checkboxes), which is
  committed. Mark items `- [x]` when they are done and tested. Decisions that
  belong to the person (names, accounts, releases) stay open items.

## Commits

- Commit and push only when the person you work for allows it. A person may give standing
  authorization for this repository, as the maintainer did for their sessions; it does not
  carry over to the sessions of others. Without it, ask before committing, and work on a
  branch for a pull request when the person has no right to push to `main`.
- Make small commits that each could be released: the code, its tests, its migration, its
  documentation and its news fragment together.
- After a push, check that the branch matches the remote and that the CI run of that commit
  passes (`gh run list --commit <sha>`); fix it if not. Do not wait for the CI while there is
  more to do: wait once, at the end, and report the result.
- Commits written by an agent end with the attribution of the model, such as
  `Co-Authored-By: <model> <noreply@...>`.

## Constraints of the code

- One class per module; a module that would need more becomes a package. The
  errors are the exception: they are grouped by topic in
  `pycal_dashboard/errors/`. `tests/quality/test_structure.py` checks this.
- Errors are split up as finely as possible: one class per cause, with a title
  and a docstring in this order: one sentence why it appears, maybe followed by the cases
  that lead to it; `Resolve:` with the actions alone, split up as "When X, do Y."; `Context:`
  (optional) that explains it; `Note:` (optional) with what fits nowhere else. They are shown
  with a link to their documentation (`docs/reference/errors.rst`); `tests/test_errors.py`
  checks the order.
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
  is decided in one place, `ProjectAccess`: readers change nothing but update from GitHub;
  writers change the project and see its collaborators and settings, but invite nobody, change
  no role or visibility and do nothing destructive; owners do everything.
  `tests/test_roles.py` checks every role with every action: a new action goes into it.
- The privacy policy (`pycal_dashboard/privacy.py`, the page `/about/privacy/`)
  always says which data of people the site keeps and who gets it: change it
  with every change of what the site keeps, shows or sends. `tests/test_privacy.py`
  fails for a model or field it does not list.
- Nothing is loaded from other sites: no fonts (such as Google Fonts), scripts
  or styles. Only the avatars of GitHub (`EXTERNAL_HOSTS` of the privacy
  policy); `tests/test_privacy.py` checks the files and the pages.
- Texts that people type to describe something are Markdown: shown with `|markdown`
  (`markdown_text.py`, cleaned by nh3) and edited with the partial `_markdown_field.html` (a bar
  of formats and a preview). `tests/test_markdown.py` checks the templates.
- People of GitHub are shown with `{% github_user %}` (`templatetags/github.py`):
  their avatar from GitHub before their name, linked to GitHub. In texts, the *GitHub handle*
  is the login, such as `niccokunzmann`, and the *GitHub name* is the display name, such as
  *Nicco Kunzmann*.
- Every link that leads to GitHub has the mark of GitHub, so that people see that they leave
  dashboard.pycal.org: `{% github_link %}` or `{% github_user %}`, else `{% github_mark url %}`
  after the text of the link in a template; links to GitHub in Markdown get it from
  `markdown_text.py`. `tests/test_github_links.py` checks the pages: add a new page with such
  links to it.
- A switch is the partial `_switch.html`; `tests/quality/test_structure.py` checks it.
- A page with public JSON goes into `pycal_dashboard/json_api.py`, which makes `/llms.txt` (the
  guideline for agents) and `/robots.txt`, and into `docs/reference/json.rst`;
  `tests/test_agents.py` checks that the guideline is complete and every address answers.
  Addresses that repeat a page many times, such as `?step=` or `?tab=`, are in `REPEATED`, so
  that crawlers leave them alone.
- The conditions of pull requests are in `pycal_dashboard/conditions/`: `condition/` (on
  `base.py`), `input/` (the kinds of inputs, which also make the fields of forms), `spec/`
  (the data the background reads and whether it is complete) and `group/` (the columns of the
  table that people choose them with). Each condition has its id, its own page
  `docs/reference/conditions/<id>.rst` with the API reference at its bottom, and is in
  `CONDITIONS`; `tests/test_conditions.py` checks them. Data whose permissions the GitHub App
  does not ask for is described but not read: asking for a permission is the person's decision.
- Every condition can be inverted, always: a condition (`Condition.negate()`) is wrapped in its
  NOT (`Not`, `conditions/condition/negation.py`), which sees through to everything but its
  name and its result, and `Not.negate()` gives the condition back; a negative condition is
  such a NOT (`label_absent` of `label_exists`), not a subclass. A column too
  (`Column.inverted()`, the NOT of a column with `not~`), in every group, filter and type; the
  page of saving a filter always has its buttons Invert and Remove. `tests/test_invert.py`
  and `tests/test_conditions.py` check every group and condition. Each condition shows its evidence on the page of a pull request: the
  least that shows why it holds or not (`Evidence`); its data specs give the links.
  A new choice of a column keeps the columns saved before as they were.
- A condition is an object made of its class and a creation spec, the inputs by name
  (`LabelExists({"label": "bug"})`), and yields the same spec again (`spec()`). All that writes
  conditions down and reads them again lives outside of them, in the factory of the conditions
  (`ConditionFactory`, `conditions/factory.py`): `create()`, `dump()` and `load()` (a spec with
  its id), `decode()` and `encode()` (the choices of a column). A group declares only which specs
  its choices mean (`specs()`) and which choices write specs (`choices_of()`); no other code maps
  choices to conditions, checks them for a column or inverts them. So a NOT and the condition
  that it is are the same: `absent` and `not~` of `present` read as one condition, written as
  `absent`. `tests/test_factory.py` checks it.
- Conditions joined by AND (`Conjunction`, `Column.joined`) are one condition of a step: one
  quality check, or one condition of Skip if. Wherever a step or a filter uses its conditions,
  go through `Conjunction.of` (its value, `encode()`, keys the texts and the skips of the step);
  a change of a column keeps its AND (`dataclasses.replace`). The AND itself is not inverted,
  its conditions are. On the page of saving a filter, a drag shows where it lands, and a drop
  where it was picked up changes nothing.
- Steps are shown to visitors by their names, never by their numbers.
- Signing out stays on the page if visitors see it, else goes a level higher in the path until
  a page answers (`signed_out.py`): so the address of a tab lies below that of its parent page,
  such as `settings/danger/` below `settings/`.
- The site names itself by its name, `SITE_NAME` (`{{ site_name }}` in templates), such as
  dashboard.pycal.org, never "this site" or "the site" in the texts that people read.
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
  `receivers.py`, never code of one trigger. `tests/test_update_paths.py` checks it. It reads
  GitHub in the background only (`UpdateQueue`, run by `UpdateWorker`, or by
  `manage.py fetch_worker` in its own process, see `FETCH_WORKER`), never while a page waits,
  except to find what a person adds. Webhooks are recorded and answered at once, and handled
  in the background (`WebhookQueue`). It writes to GitHub only in the background, after an
  update, for the actions of steps: the labels of a step that an open pull request
  completed (`StepCompletion`, a receiver; each write is an `Action` in the log).
  The first time it sees a pull request it only records its step, so nothing is
  written for what happened before. A comment on pull requests may follow.
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
  A module without such packages is imported at the top instead.

## Tests

- Every change comes with tests, also of the errors people can see.
- Run `make lint`, `make test`, `make browser-test` and `make docs` (and `make prose` when the
  documentation changed) and report the results as they are, failures included.
- `tests/benchmark/` times the pages with many pull requests (`make benchmark`); it is not part
  of `make test`.

## Translations

- Texts are marked for translation and extracted (`make messages`), but translated only when the
  person asks: ask before translating. Until then a text shows in English. `make messages`
  guesses no translations (no fuzzy matching). The site speaks English, German and Spanish.

## Changelog and documentation

- Every change people notice has a news fragment in `news/`, named without `.rst`, such as
  `news/+topic.feature` or `news/12.bugfix`. The documentation shows them in the changelog:
  `docs/conf.py` drafts them with towncrier at each build.
- The documentation (`docs/`) is updated with the change.

## Codex

- Codex reads this file. It records prompts with the hook of `.codex/hooks.json`, which each
  person approves once in Codex (the hook approval prompt, **Codex Settings → Hooks**, or
  `/hooks` in the CLI); see *AI prompt recording* below.
- `make dev` and `uv sync` need the network once, to install the packages; the checks do not.
  In a sandbox without the network, run the checks with the installed `.venv`
  (`uv run --offline`, or the targets of `make`), and say which checks could not run.
- `make messages` needs gettext or Docker; when neither is there, say so instead of editing
  the compiled `django.mo`.

## Claude Code

- Claude Code reads `CLAUDE.md`, which includes this file; put new rules here, not in
  `CLAUDE.md`, so that every agent follows them. It records prompts with the hook of
  `.claude/settings.json`.
- What Claude remembers in its own memory is not shared with the team: a rule that matters for
  everybody goes into this file.

<!-- ai-prompt-auto-commit: start -->
## AI prompt recording

At the start of a session, read [.github/assistant-guidelines.md](.github/assistant-guidelines.md).
Follow its instructions for reminding contributors to activate prompt-recording
hooks and for storing prompts without duplicates.
<!-- ai-prompt-auto-commit: end -->
