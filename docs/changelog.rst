=========
Changelog
=========

.. The changes since the last release: towncrier drafts them from news/ at each build of the
.. documentation (docs/conf.py). towncrier build writes the release below the next line.

.. include:: _build/unreleased.rst

.. towncrier release notes start

0.7.1 (2026-11-21)
------------------

New features
~~~~~~~~~~~~

- PR Sync: the tab Scope is Synchronization, with the Pull request selection and its Options, and the button Keep N pull requests synchronized.


0.7.0 (2026-11-21)
------------------

New features
~~~~~~~~~~~~

- About: the tab About is Contact, with tiles to the documentation, to report a problem or leave feedback, and to the changelog; Version and GitHub App are tabs of their own.
- The actions of a step: When a pull request leaves the step, instead of completes; they also follow when the step is skipped while the pull request is in it.


0.6.0 (2026-11-21)
------------------

New features
~~~~~~~~~~~~

- The message of PR Sync is not lost while it is edited: the edited message is saved while it is written and stays until Apply makes it the current one, which says Applied in green once they are the same. The tabs are Current Message (with Message, Markdown and Edit above it), Edit and Preview side by side, Status Label and Scope, which is of the message and the step labels.
- The step labels: Apply, Synchronize, and above Apply what it does, such as Create the labels Step: Review and label 3 pull requests, or Delete the labels from the repositories.


Bug fixes
~~~~~~~~~

- The fields of Markdown are as wide as their form.


0.5.0 (2026-11-21)
------------------

New features
~~~~~~~~~~~~

- A group of conditions Dashboard, on data of dashboard.pycal.org: PR Sync on (the pull requests with the Status Message) and a skipped step, to filter by them.


0.4.0 (2026-11-21)
------------------

New features
~~~~~~~~~~~~

- The tab PR Message is called PR Sync, with the tabs Status Message (the message as before) and Status Label: the step labels, as a table of the choices Off (no step labels; saving it deletes them on GitHub, for owners) and With PR Sync (people label pull requests by hand, and the labels go on the pull requests with the PR Sync on). The labels that were automatic or manual are With PR Sync now.


0.3.2 (2026-11-21)
------------------

Bug fixes
~~~~~~~~~

- Skipping a step: the reason is asked in a dialog that pops out, the step says Skipped by @handle: reason in the row of The pull request is here, and Don't skip undoes it.


0.3.1 (2026-11-21)
------------------

Bug fixes
~~~~~~~~~

- The swatches of the choice of the color of a step suit dark pages, too: there they show the dark tint that the step gets.


0.3.0 (2026-11-21)
------------------

New features
~~~~~~~~~~~~

- The page Account has tabs: Email addresses, with everything of /accounts/email/ (add, verify, make primary, remove), Preferences, The GitHub App and Delete the account. The menu of the account no longer has Email addresses.


0.2.0 (2026-11-21)
------------------

New features
~~~~~~~~~~~~

- The overview of a project no longer reloads itself while it updates: the box Updating reads itself again every 10 seconds, with a turning circle, and shows a check mark and the new numbers when the update is done.


0.1.0 (2026-11-21)
------------------

Breaking changes
~~~~~~~~~~~~~~~~

- The GitHub App asks for the permissions ``checks``, ``statuses`` and ``contents`` (read) and the
  webhooks ``label``, ``check_run``, ``check_suite``, ``status`` and ``push``, so that the conditions
  of pull requests work: the owners of each installation accept them on GitHub, and the site tells
  them by email.
- The GitHub App asks for write access to pull requests, to add and remove labels and to create and update a comment of the site. The owners of the installations accept it on GitHub; the people of the installations and of the projects with their repositories are told by email.


New features
~~~~~~~~~~~~

- The frame of the dashboard of the PyCalendar community: its GitHub App that only receives webhooks, sign in with GitHub through an OAuth app, the account page with the button to install the app, the Django admin for the administrators and the JSON API. (`#1 <https://github.com/PyCalendar/dashboard.pycal.org/issues/1>`_)
- /robots.txt lets robots read the public pages and their JSON, and /llms.txt is a guideline for
  agents: the JSON of every public page and how to navigate it. /index.json lists the projects and
  the guideline.
- A label renamed on GitHub is renamed on the site too, found by its id, and in the saved filters
  that name it, so they keep working.
- A new tab PR Message writes a message about the state of each pull request as a comment on it and keeps it up to date: its template with the variables of steps and of the tasks, a live preview with its Markdown, and the scope of the pull requests that get it.
- A page of a person in a project, /projects/<project>/contributors/<handle>/, with the tabs Profile,
  Reviews, Issues and Pull requests and their counts.
- A project is at ``/projects/<address>/`` and its pages below it, such as
  ``/projects/icalendar/settings/``, without its name. The addresses with the name lead there.
- A pull request that no task of any step applies to is outside of the usual steps: its page shows all steps gray with a note, and its badge says outside. Check on the tab Steps lists these pull requests.
- A saved filter saves itself while it is edited, and its page has Edit the conditions and the
  step at the top right. Readers go from a filter to its step and from a step to its filter, and
  see only the visible steps.
- A step adds and removes labels when a pull request enters it and when it completes it, each a list separated by commas; labels renamed on GitHub are renamed there, too.
- A step can add labels to a pull request that completes it: the GitHub App adds them when an update finds the pull request out of the step with all its tasks done.
- A step can be hidden in the page of a pull request: it shows there only when the pull request is in it.
- A step saves itself while it is edited: a moment after typing and when a field is left, with
  Saving and Saved at the bottom instead of a button. The menu Variables of the editor links the
  documentation of the variables instead of listing them.
- Activity on GitHub, which the webhooks of the GitHub App tell of, updates the repository it is
  about in the background: what changed since its last update.
- An update keeps all issues and pull requests of the repositories, open and closed, with their
  title, description, times and who created them (GitHub users, linked to the people who sign in).
  After a migration that changes what the site keeps of GitHub, the repositories are updated again in
  the background.
- CI scans the image with Trivy, checks the prose of the documentation with Vale, deploys every push of ``main`` with Sencho and then checks the live site (``make check-live``); the administrators read the log of the site on ``/logs/``.
- Conditions of a filter read as sentences, such as ``it does not have the label bug``, and the page of
  saving says that the filter shows a pull request when one of them is met; its switches are larger,
  with a thick border when on. Nobody is signed out automatically by default (``SIGN_OUT_MINUTES``
  is 0).
- Creating a project offers Public, the default, and Private side by side, each with what it means.
- Each pull request has a badge with its step and tasks done, such as Triage 3/4, at the address of its page with ``badge.svg`` or ``badge.png``; it is drawn once and cached until something changes. The table of pull requests shows it in the new column Step, linked to the page of the pull request.
- Each pull request has a page in its project: a bar of the steps with a square for each task, done in green and to do in red, and the tasks of the step it is in, those to do first.
- Every account can install the GitHub App, which is public now; the error pages of a missing GitHub App or OAuth app lead to its setup page. The preference of emails is removed until the site sends emails.
- Every hour, the repositories not read in the last day are updated, which renews what no webhook
  tells of, and an overview that may be out of date starts its update when it is opened. Every
  update takes the same path and sends signals after it; a project is as fresh as its oldest
  repository.
- Every public page has its JSON at ``<page>.json`` for other sites (CORS), instead of ``/api/v1/``; the page ``/licenses/`` lists the licenses; times show in the local time of the browser; links to the documentation are an open book and links to GitHub show its mark.
- Every switch is one partial and looks and works the same: a thick border that only changes its
  color, with the role of a switch for screen readers.
- Filters: Save next to the number of pull requests saves the columns of conditions, in their order
  and with what each shows, as a filter of the project with a name and a description in Markdown.
  The page of saving sums the columns up and suggests the opposite of a column that shows only what
  it does not apply to. The tab Filters lists them with how many pull requests each shows and opens
  them in the table, where they are saved again or as new filters; also as JSON.
  CI has three switches: passing, failing and unknown (the new condition ``ci_unknown``), and a
  question mark says why a result is not known. Addresses keep labels readable.
- German and Spanish translations of the new texts: conditions, the Markdown editor, deleting the
  account and the roles.
- In a step, the conditions of its filter are called its tasks.
- In the bar of the steps, the arrow to move a step left is left of its name and the arrow to move it right is right of it; the arrows of the order of the steps are between the boxes. The switch that hides a step has the size of every switch.
- In the page of a pull request, the steps it went through are green, the step it is in is yellow or red, and the steps after it are gray without numbers; the badge cannot be copied there any more.
- Links to the documentation are an open book instead of a question mark.
- Lists of tasks in Markdown, - [ ] and - [x], show checkboxes as on GitHub, such as in the preview of the message; they cannot be changed there.
- Markdown shows images of this site, such as the badges; images of other sites are removed.
- Notifications are laid out as title, button, permissions and text. The people of an installation
  are told only about the permissions the GitHub App already has, since GitHub asks for no others;
  the notification of the app comes first.
- Notifications: a number at the account menu counts the unread ones, and the page Notifications
  lists them, marks them as read and shows those that are done. The people of an installation that
  needs more permissions are notified, also without emails, with the two steps on GitHub; the
  administrators are notified while the GitHub App itself lacks permissions or events. The menu no
  longer installs the GitHub App: adding repositories does. The table of pull requests has no button
  of JSON: the reference of the JSON describes it.
- People add email addresses, verify them with a link that the site sends, choose the primary one and remove the others; the emails and the pages speak the language of the person.
- People are signed out an hour after signing in (``SIGN_OUT_MINUTES``); ``FAVICON`` and ``FOOTER_LINKS`` brand each site; the start names ``SITE_ADMINS`` that never signed in.
- People choose their language and the colors (as the system, light or dark) in their account, for every device; without a choice, the browser and the menus decide.
- People delete their account in the red area at the bottom of the page Account, after typing
  their GitHub name: with their token, email addresses, preferences, roles and the projects that
  have nobody else. The only owner of a shared project gives the role own to another person first.
- People of GitHub are shown with their avatar from GitHub before their name, linked to GitHub.
  Sharing a project proposes the people who signed in, with their avatar and name.
- Permissions and events of the GitHub App show as GitHub names and describes them, grouped as on its
  settings page. The tab Filters counts the pull requests of a filter and its conditions only when it
  is opened, and has a button Edit. The page of saving a filter has no column Shows, and its
  switches have room.
- Projects are at ``/projects/<address>/``. A new project gets a random address of six hexadecimal digits unless its creator chooses one; owners change it, and the site suggests one after the repository of a project of one repository (``icalendar``, ``collective~icalendar``, ``collective~icalendar-2`` ...). Addresses have the letters of a GitHub handle and at most one ``~``. Every address a project had is kept in its history, leads to the project and is never given to another one.
- Projects: people who signed in create projects, sets of repositories on GitHub, with a name and a description, public or private, and add repositories by name with proposals while they type, from one of their organizations or by a search. The overview of a project shows its open issues and pull requests, when it was last updated and whether it is up to date; *Update* reads the repositories in the background with a progress bar. Owners share a project with others, who may read, change or own it. The page *Projects* is in the menu.
- Readers of a project may update it from GitHub. Only the owners restore a backup, as it replaces the filters and steps; a writer who sends another visibility is refused.
- Repositories added to a project are read from GitHub in the background at once, without pressing
  Update.
- Saving a filter under the name of another one asks whether to replace that filter, instead of an error.
- States of people, counted in all repositories of a project: ``pull_requests_opened``, ``own_pull_requests_closed``, ``reviews_given`` and ``review_ratio``. They share their code with the conditions: a condition is a state that is true or false.
- Status labels of the steps on GitHub, such as Step: Review, on the pull requests with the PR Message: automatic (the site sets them) or manual (people do). A label that a person adds puts the pull request into its step; of several, the one added last stays. Labels renamed or recolored on GitHub rename or recolor their step.
- The GitHub App subscribes to the webhook ``public``: a repository made public, or private (the
  webhook ``repository``), is updated at once, so that visitors of public projects see only public
  repositories. The owners of the app add the webhook, see the notifications.
- The address of a step, steps/?step_id=<id>, stays when the steps move; one of a removed step shows a notice instead of an error.
- The background work runs in a process of its own in the container, as in community-insights (FETCH_WORKER, external-http-container by default): webhooks are recorded and answered at once, and the worker handles them, the updates and what follows them; it is started again when it stops, such as out of memory. Both processes share the cache, in files of the data folder.
- The button that removes a step is red.
- The columns of conditions filter as an or: a pull request shows when any column that filters
  shows it.
- The condition Reviews has the switch Also count comment reviews: reviews of comments only count, too.
- The conditions ``reviews_at_least`` and ``review_ratio_above``, and the columns Reviews and Author of the table of pull requests.
- The conditions of numbers compare above, below, at most, at least or exactly: the columns Reviews (at least by default) and Author (below by default), and the conditions ``reviews`` and ``review_ratio``, which replace ``reviews_at_least`` and ``review_ratio_above``; columns saved before keep working.
- The conditions of pull requests, not shown on the pages yet: ``label_exists``, ``label_absent``,
  ``ci_passes``, ``ci_fails``, ``merge_conflict``, ``branch_outdated`` and ``auto_merge_enabled``, each
  with its inputs, the data it needs and its page in the documentation. The update of a repository
  keeps its labels and the labels of its issues, and the state of its open pull requests: whether
  they can be merged, are behind their base, and merge themselves.
- The container needs about half the memory when idle (about 60 MB instead of 124 MB): one process of nginx and of gunicorn by default (``WORKERS=1``), the packages that speak with GitHub are loaded only when needed, and the image reads the licenses when it is built.
- The description of a project is Markdown: the bar above the field formats it (bold, italic,
  links, lists, quotes, code), Preview shows it, and the pages show it as Markdown, cleaned of
  anything dangerous.
- The editor of Markdown has a menu Variables in its bar for the templates of steps: a click inserts
  the variable where the cursor is. The descriptions of the conditions of a step are written in the
  editor of Markdown, too.
- The editor of a step has Edit the filter, a color for the background of the step, and the switch Visible in the page of a pull request, on by default; Preview shows a template with an example pull request.
- The footer links the page About and the extra links only: the documentation, the code and the
  version are on the page About. The page About tells what the site keeps of GitHub and what the
  app may write.
- The header of a column of conditions is short: the label (struck through when absent) or the
  states chosen; below it a gear and two toggles of the check marks and crosses filter at once, one
  always on. The label is shown in the header only.
- The menu of a column of CI explains unknown: the checks are read for open pull requests only, so closed and merged ones are unknown.
- The menu of the account has My projects: the projects you are a collaborator of.
- The message of the pull requests is edited in four pages: the message, the editor, the review with example pull requests that each differ in their step or the state of a task, from no task done to all of them, or any pull request by its number, with a link to edit the step it is in, and the scope.
- The overview of a project says *Updated* for the time a repository was updated from GitHub, and
  speaks of updates everywhere, not of reading.
- The overview of a project shows its update at the bottom, as one line while it is up to date.
- The page *Register the GitHub App* and ``manage.py check_app`` name the permissions and events that the app lacks; a guide tests the app locally through Tailscale Funnel; ``.env.development.example`` holds the settings for development.
- The page About has the tabs About, Privacy and Licenses. The privacy policy says which data of
  people the site keeps, who sees it and who else gets it. The pages load nothing from other sites
  but the avatars of GitHub.
- The page of a pull request names its step without its number.
- The page of a pull request, its badge and the message use the results of the conditions that the site keeps, and ask the database a few times only.
- The page of a saved filter is called Edit the filter, with a button next to its title that says
  whether it is saved and turns while it saves.
- The page of saving a filter has Invert and Remove at each condition, and a new filter starts with every condition on.
- The page of saving a filter lists its conditions in one table with their long names; a switch
  turns a condition off, which grays it out: it stays a column but does not filter.
- The page of the message shows its examples in every state of the steps and a pull request by its number to everybody, also without signing in.
- The pages call the login on GitHub, such as niccokunzmann, the GitHub handle, and the name, such as Nicco Kunzmann, the GitHub name. Sharing a project proposes everyone who signed in.
- The people of a project are its collaborators: the tab Collaborators is at
  ``/projects/<address>/collaborators/``, and the old address of the tab People leads there.
  The only owner of a project cannot change their role or leave on the page.
- The roles of the collaborators link the documentation of what each role may do.
- The section Install the GitHub App of the repositories of a project shows up only while a repository
  lacks the app or the permissions it needs now. The button Show its repositories is called Show
  repositories.
- The settings of a project download a backup of it as YAML, with its repositories, filters and steps, and restore it; the documentation describes the format.
- The site keeps the GitHub name of each person, their handle on GitHub, taken at every sign in; projects are shared by it. The sign in also reads the organizations of the person (scope ``read:org``, read only).
- The site reads the reviews of all pull requests and who closed them; the repositories are read again after the update.
- The site records the installations of its GitHub App with their permissions; when an installation lacks permissions that the site needs, the people who installed or changed it get an email and see it on their page *Account*, with the link to accept them.
- The site speaks English, German and Spanish: the language comes from the browser, and the menu with the globe keeps another choice.
- The start page has no cards of the GitHub App and the account anymore: the menu leads to them, and
  the GitHub App is installed when repositories are added to a project.
- The state of open pull requests, their checks and auto-merge come with one query of GraphQL
  for each repository, instead of three requests of the REST API for each pull request: far fewer
  of the requests GitHub allows per hour.
- The tab Filters has a button New filter that opens the table of pull requests with the menu to add a condition.
- The tab Filters shows a loading animation while it counts the pull requests of a filter.
- The tab Filters shows only the conditions in force; those that are off appear only in the table of
  pull requests and when a filter is edited.
- The tab Pull requests is a table: Display chooses its columns (status, title, organization,
  repository, number, creator, created), which CSS shows and hides at once; first the title, the
  number and the creator. The title and the number link the pull request on GitHub, an icon only
  without both; without the status, each row starts with the color of its status. A menu at the top
  right shows 10, 25, 50 or 100 a page, also for the JSON (``per_page``, at most 100). The filters by
  state are removed.
- The tab Pull requests of a project lists the pull requests of all its repositories together, public
  like the project, open, merged or closed; the tile of open pull requests on the overview leads
  there.
- The tab Steps explains the steps in simpler words.
- The tab Steps: the steps a pull request goes through, each a saved filter of the conditions that
  keep it there, in a bar from left to right that is ordered by dragging or with arrows. A step has a
  name and a summary, and each condition a summary and a description that guide people to remove
  it; they are templates with variables, which stay text. Filters become steps on the tab Filters.
- The table of pull requests gets columns of conditions with the button +: a label present or
  absent, the branch (up to date, outdated, conflict), the CI (passing, failing: the last complete
  result) and the status (open, closed, merged, auto-merging). Each cell shows a green check mark or
  a red cross and why; each column can filter the table, and its gear changes, moves or removes it;
  columns can be dragged. The address keeps them, and the JSON has their results. The new
  condition ``branch_up_to_date``. The table shows the GitHub name of the creator without the full
  name.
- The tables of pull requests, the filters and the steps are fast also with many pull requests: the conditions read the data loaded once, the results of each column are kept until the next update, and the site prepares those of the saved filters after each update. ``make measure-speed`` measures every condition on the live site.
- The tabs Collaborators and Settings are only for the writers and owners of a project: readers and visitors no longer see who the collaborators are.
- The tasks of the message have their descriptions on the lines below each item of the list, indented so that they belong to it.
- The tasks on the page of a pull request show the evidence of their conditions: links to the
  checks, the box where it is merged, the pull request, as many reviews as decide the condition,
  and the page of the author.
- The variable ``{pr_steps_url}`` is the address of the page of the pull request with its steps.
- The variables of the badge are a group of their own, Badge, and their addresses always name the repository, so they stay the same when the project gets another repository.
- The variables of the templates of steps are grouped, with examples in the documentation; new are ``{author_mention}``, ``{author_name}``, ``{author_handle}``, ``{pr_title}``, ``{pr_number}``, ``{step_name}``, ``{step_number}`` and ``{step_id}``.
- Three more conditions: ``open``, ``merged`` and ``closed`` (without being merged).
- When GitHub is busy or a query takes too long (502, 503, 504), the site asks again, with smaller
  pages of pull requests, and reads only what each installation accepted. The overview of a project
  shows failed updates at the top, in a notice that can be clicked away, with details to copy: the
  request, the answer and request id of GitHub, the time and the version, without tokens or data of
  people.
- Writers skip a step for a pull request with a reason, and remove the skip again; the pull request is then in the next step. Steps skip themselves for the pull requests of the authors they name. The boxes of the steps of a pull request are aligned in rows.


Bug fixes
~~~~~~~~~

- A long update no longer gets the process of gunicorn killed: it may be busy for TIMEOUT seconds (120 by default) instead of 30. Webhooks stay in the memory of nginx, the requests are logged once, and the log says how long the work after an update takes when it takes over a second.
- A sign-in whose token GitHub refuses says to sign out and sign in again, instead of blaming the GitHub App.
- Opening a filter on the tab Filters shows the table of its conditions at once; their numbers are
  filled in when they are counted.
- Pages served at the same time cannot stop each other in a deadlock while they import the packages that the site loads only when needed: every lazy import goes through an import guard.
- Robots leave alone the addresses that only show the same pages again, such as every pull request with every step, the columns of the table and the badges.
- The bar at the top stays one row on phones again: the menus of the columns of conditions had
  taken its class. The menus of + and of the gear have a cross that closes them without a change;
  so does Escape.
- The colors of steps suit dark pages, too: their background is computed from the color, light on light pages and dark on dark pages, also for strong colors from labels.
- The completion of repositories and of people also proposes what was typed before the page was
  ready. A GitHub user without an avatar of their own shows the avatar of GitHub for their name.
- The documentation links lead to their sections: the license, and the administrators. The page
  About links all licenses.
- The notification that the GitHub App lacks permissions or events resolves itself: the site checks
  the app every hour, at each webhook of an installation, and with Check again. The filters of the tab
  Filters have no bullets.
- The page shown while the site restarts no longer leads to 405 Method Not Allowed after a form was sent: with JavaScript it waits for the site and opens the page again with GET, or goes back to the page of the form.
- The table of pull requests keeps the filter it shows when its columns change, so that saving it again keeps its name, also on the way from a step.
- The times that the browser writes, such as ``on 3 Oct 2026``, are in the language of the page: the
  server gives the script its translation. ``branch_up_to_date`` documents its special case: a merged
  pull request is always up to date.


Documentation
~~~~~~~~~~~~~

- The changelog of the documentation shows the changes since the last release, drafted by towncrier from the news fragments at each build.


Maintenance
~~~~~~~~~~~

- Every kind of data the site keeps of GitHub has the webhooks that tell of its changes, with the
  permissions GitHub needs to send them; a test checks it.
- The browser tests sign in through the OAuth flow with a fake GitHub, and the browser reaches nothing but the site, also on redirects.
- The names of the permissions of GitHub, copied from GitHub, are under their license, CC-BY-4.0, which the page Licenses shows.
- The new texts are translated into German and Spanish.
- make messages guesses no translations: a new or changed text shows in English until it is
  translated, and the tests allow it.
