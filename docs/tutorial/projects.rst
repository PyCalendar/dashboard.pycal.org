========
Projects
========

A project is a set of repositories on GitHub that people look at together,
such as the repositories of the Python Calendaring Ecosystem. Its page shows
how many issues and pull requests are open.

The page *Projects*, in the menu at the top, lists every public project, and
the private projects you have a role in.

Create a project
================

Sign in with GitHub, open *Projects* and press **+ Create a project**. Enter:

- the **name**, such as *icalendar*,
- the **description**: what the project is about, in Markdown. The bar above
  the field makes text bold or italic, adds links, lists, quotes and code;
  **Preview** shows it as the page will. Without JavaScript, you type the
  Markdown yourself, such as ``**bold**`` and ``[a link](https://pycal.org)``.
  Images show only from this site, such as the badges of pull requests: the
  site loads nothing from other sites.
- the **visibility**: *Public*, the default, for everybody, or *Private*, only
  for its collaborators, see :ref:`project-roles`,
- optionally its **address**, see :ref:`project-address`.

You own the project you create. Next, the site asks for its repositories.

.. _project-address:

The address
===========

A project is at ``/projects/<address>/``, such as ``/projects/icalendar/``,
and its pages below it, such as ``/projects/icalendar/settings/``. Links of
before, with the name of the project after the address, lead there.

- Without a chosen address, a project gets a random one of six hexadecimal
  digits, such as ``3f9a0c``; also a project made in the Django admin.
- An address has the letters of a GitHub handle: ``a`` to ``z``, ``0`` to
  ``9`` and single hyphens inside, and at most one ``~`` between an account and
  a repository, such as ``collective~icalendar``. Capital letters become small
  ones. ``new`` belongs to the site.
- When the project has one repository, the site suggests an address after it:
  the name of the repository, such as ``icalendar``; if another project has it,
  ``collective~icalendar``; then ``collective~icalendar-2``, ``-3`` and so on.
  Press *Use it* on the tab *Repositories* or *Settings*.
- The owners change the address on the tab *Settings*. Old links keep working:
  the old address leads to the new one. Every address a project had is kept
  with the time it was used, listed under *Old addresses*, and no other project
  ever gets it, also after the project was deleted. A project may go back to an
  old address of its own.

.. _add-repositories:

Add repositories
================

On the tab *Repositories* of the project, add repositories in one of three
ways:

By name
   Type ``owner/name``, such as ``collective/icalendar``, or paste a link to
   the repository. While you type, the field proposes the repositories that the
   site knows and those of all of GitHub. Without JavaScript, it proposes those
   the site knows.
From an account
   Choose yourself or one of your organizations and press *Show its
   repositories*, then tick the repositories and press *Add the chosen
   repositories*.
Search
   Search all of GitHub by name and tick the repositories you want.

A repository can be in several projects. To list your organizations, the site
reads them with the token that GitHub gave it when you signed in (the scope
``read:org``, read only). If the site has no token of yours, it says so: sign
out and sign in again.

.. _private-repositories:

Private repositories
====================

A private repository can be added only

- to a private project, and
- if the GitHub App is installed on it, and
- if you may read it on GitHub.

The site finds it through its GitHub App: type its name. It never asks your
GitHub account for access to private repositories. A project with private
repositories cannot be made public. Only the collaborators of the project see them;
if a repository of a public project becomes private, the visitors no longer
see it.

Install the GitHub App
======================

After adding repositories, the tab *Repositories* says on which of them the
GitHub App is installed. The section *Install the GitHub App* shows up only
while a repository lacks the app or the permissions it needs now. Installed,
the app lets the site

- receive the webhooks of the changes in the repositories,
- add and remove labels of pull requests,
- create and update a comment of the site on a pull request.

:doc:`/reference/permissions` lists the permissions it asks for and why. An
owner of the account of a repository installs it with **Install the GitHub
App**, see :doc:`/how-to/install-app`.

When a new version of the site needs more permissions, the writers and owners
of the projects with a repository of the installation get an email with the
link to the page on GitHub where the permissions are accepted, see
:ref:`new-permissions`.

.. _project-update:

The overview and the update
===========================

The overview of a project shows the number of open issues and open pull
requests of all its repositories and of each one. At the bottom, it says
whether the project is up to date and when it was last updated, in your time
zone.

When repositories are added, the site updates them from GitHub in the
background at once. **Update** updates them again. A progress bar shows how many
are updated; the page reloads itself until the update ends. The project is *up
to date* when every repository was updated in the last day without an error. A
repository that could not be updated shows why: a notice at the top of the
overview names each one with its error, linked to the documentation of the
error. Its *Details to copy* hold what helps to find the cause, such as the
request, the answer of GitHub and its request id, the time and the version of
the site, but no tokens or data of people; paste them into a bug report or a
question. The cross clicks the notice away until a new failure comes.

The site reads a repository with the token of the GitHub App when the app is
installed on it, else without a token, which works for public repositories.
An update reads all issues and pull requests, open and closed: their title,
description, times, and who created them. The first update reads them all;
the next ones read only those that changed.

With the GitHub App installed, activity on GitHub, such as a new pull request
or a comment, updates its repository in the background: the webhook of GitHub
tells the site. Every hour, the site also updates the repositories that were
not read in the last day, which renews what no webhook tells of; and the
overview of a project that may be out of date starts its update when someone
opens it. A project is as fresh as its oldest repository.

.. _project-pull-requests:

Pull requests
=============

The tab *Pull requests*, public like the project, lists the pull requests of
all its repositories together, the newest first: 10, 25, 50 or 100 a page,
as the menu at its top right chooses. The tile with the number of open pull
requests on the overview leads there.

*Display* chooses the columns: the status, the title, the organization, the
repository, the number, the creator with their avatar, and when it was
created. First it shows the title, the number and the creator; the browser
keeps the choice. The title and the number link the pull request on GitHub;
without both, an icon of GitHub links it. Without the status, each row starts
with the color of its status: green while it is open, purple when it was
merged, red when it was closed without merging.

.. _condition-columns:

Columns of conditions
---------------------

The button **+** at the right of the table adds a column of conditions; each
says for every pull request whether its condition applies, with a green
check mark, or not, with a red cross, and why:

**Label**
   A label is present or absent. Choose a label of the repositories or type
   another one; the cell shows the label in its color.
**Branch**
   Up to date, outdated or in conflict with its base branch, as many as you
   switch on; a merged pull request is up to date. The cell names what applies.
**CI**
   Passing or failing: the last complete result of the checks, also while new
   ones run.
**Status**
   Open, closed, merged or auto-merging, with their colors.
**Reviews**
   The pull request has a number of reviews: *at least* (the default), *at
   most*, *more than*, *fewer than* or *exactly*. At least and at most include
   the number. Approvals, requested changes and reviews dismissed later count,
   comments do not. The cell shows how many it has.
**Author**
   A state of the author compared with a number, counted in all repositories
   of the project that you see: the review to pull request ratio, the reviews
   given, the pull requests opened, or those of them closed by the author;
   *below* (the default), *above*, *at most*, *at least* or *exactly* the
   number. The ratio is the reviews given for each pull request that the
   author opened and did not close themselves: *1* is as many reviews as pull
   requests, *0.5* half as many and *2* twice as many. The cell shows the
   number of the author. See :doc:`/reference/states/index`.

The header of a column is short: the label, struck through when it must be
absent, or the states chosen, such as *conflict*. Below it, the gear changes
the column, moves it or removes it, and two toggles filter the table at once:
the check mark shows the pull requests the condition applies to, the cross
those it does not apply to. One of them is always on: switching off the last
one switches the other one on. The filters are an *or*: a pull
request shows when any column that filters shows it; a column with both
toggles on does not filter. Drag a column onto another one to move it. The
columns of conditions stay right of the other columns. The address of the page
keeps them, so it can be bookmarked and shared; the JSON has the result of each
column for each pull request (``conditions``), see :doc:`/reference/json`. A
question mark means that the data of the pull request is not complete yet, such
as checks that were never read, or reviews of a repository without the GitHub
App. See :doc:`/reference/conditions/index`. The site keeps the results of the
columns until a repository of the project is updated, so the table opens fast
also with many pull requests.

The tabs of a project are always in this order: the overview, the public tabs,
then those of the collaborators.

.. _project-filters:

Filters
=======

**Save** next to the number of pull requests saves the columns of conditions
as a filter: their order and whether each shows the pull requests it applies
to, those it does not apply to, or both. The page of saving asks for a name,
unique in the project, and a description in Markdown, and lists the conditions
in one table, with their long names, such as *Label needs review: present*, and
whether each shows the pull requests it applies to or those it does not. They
filter as an *or*. A switch at each condition turns it off: it is grayed out and
stays a column of the table without filtering; when a filter is saved the
first time, every condition is on. **Invert** next to a condition turns it
into its opposite, such as *it is not auto-merging* for *it is auto-merging*
or *fewer than 2 reviews* for *at least 2*, and **Remove** removes it. For a condition that shows only
what it does not apply to, the page suggests its opposite where it is the same,
such as *label absent* for not *label present*; **Use it** switches it.

The tab *Filters*, public like the project, lists the saved filters with their
description. **+ New filter** opens the table of pull requests with its menu **+**
open, to add the first condition of a new filter. Opening a filter shows a
loading animation while it counts the pull requests it shows and those each of its
conditions applies to. It shows only the conditions in force: those that are
off are no part of the filter and appear only in the table of pull requests and
when the filter is edited. **Pull requests** opens them with the filter, and
**Edit** opens the page of saving. There it can be changed, and saved
under its name or as a new filter. Writers and owners save filters.

A filter names its labels; a label of that name in any repository of the
project counts, in any case. When a label is renamed on GitHub, it keeps its
id: the next update of the repository finds it under its new name and renames
it in the saved filters, too, so that they keep working. New labels and
renames come with the webhook ``label``, or with the hourly update.

.. _project-steps:

Steps
=====

The tab *Steps*, right of *Filters*, shows the steps that a pull request goes
through, from left to right: *Step 1 → Step 2 → Step 3*. Each step is a saved
filter. In a step, the conditions of its filter are called its *tasks*: what
keeps a pull request in it, such as a conflict or a missing review, to be done
before it can be merged. A pull request is in the left-most step with a task
for it, a condition of the filter that applies, and in no step when none does.

There are no steps until they are made: **Make it a step** next to a filter on
the tab *Filters*, or the button **+** of the tab *Steps*, adds the filter as
the last step. Drag a step in the bar to move it, or use its arrows; steps more
to the left come first.

A click on a step shows it below the bar, with **Edit the filter** at the top
right, which opens the page of saving its filter. Its name is that of its filter
until you change it, and its summary is a template in Markdown. A click on a
task opens its summary, a line of text, and its description, which guides
people to do it, such as with a link to the documentation; the description is
written in the editor of Markdown, too. They take variables: the menu
**Variables** in the bar of the editor inserts the one you click where the
cursor is, see :ref:`step-variables`. **Preview** shows the text with an example
pull request, and says so when it uses variables. A step saves itself while you
edit it.

*Color* gives the step a color, the background of its box in the bars of the
steps, or none. The switch *Visible in the page of a pull request*, on by
default, shows the step in the bar of that page; switched off, the step shows
there only when the pull request is in it, and the bar of the tab *Steps*
marks it *hidden*.

Below the tasks, *When a pull request completes the step* lists the labels
that the GitHub App adds to a pull request that completes the step: one of the
repositories, or a new one, which GitHub then creates. A pull request completes
a step when an update finds it no longer in the step, with all tasks of the
step done, while it is open. The site remembers the step of each open pull
request at every update; the first time it sees a pull request, it only
remembers where it is, so nothing happens for steps completed before. The log
of the site records every label added. Leave a field empty to remove its label.

**Check** next to the button **+** lists the pull requests outside of the
steps: no task of any step applies to them, so a filter of a step may lack a
condition for them. It lists the open pull requests, or all of them, also the
closed and merged ones, which are mostly outside as they are done.

.. _pull-request-page:

The page of a pull request
--------------------------

The title of a pull request in the table opens its page,
``/projects/<slug>/pull/<number>/``, public like the project. When several
repositories of the project have a pull request of the number, it asks which.
At the top, a bar shows every step of the project in its order, with its name
and a square for each task. The steps the pull request went through, left of
the step it is in, have a green border and a check mark. The step it is in, the
left-most one with a task to do, says so and shows how many of its tasks are
done, such as *1/3*: its squares are green for a task done, on the left, and red
for a task to do, on the right, gray while its data is not known yet; its
border is yellow when some tasks are done and red when none is. The steps after
it are gray, without numbers. Hidden steps are left out, unless the pull request
is in one. The step shown below the bar has a darker background. When no task of any
step applies to the pull request, all steps are gray and a note says that it is
outside of the usual steps it should take, such as a merged pull request.

A click on a step shows its summary and its tasks below the bar. The tasks to do
come first, marked *TODO* and open, with their description; the tasks done have
a green check mark and are closed. The summaries and descriptions show the
values of the pull request in place of the variables.

.. _pull-request-badge:

The badge of a pull request
---------------------------

Each pull request has a badge with the step it is in and how many of its tasks
are done of all of them, such as *Triage 3/4*; *Steps: outside* when no task
of any step applies, and
*Steps: none* without steps. It is at the address of its page with
``badge.svg``, or ``badge.png`` for places that show no SVG, such as
``/projects/icalendar/pull/42/badge.svg``; when several repositories of the
project have pull requests, the address names the repository with
``?repository=collective/icalendar``. A badge is always a link to the page of
its pull request. The column *Step* of the table of pull requests shows it,
and the variable ``{pr_badge}`` puts it into a summary or description.

The site draws a badge once and keeps it until the repositories are updated or
the steps change; browsers and GitHub keep it for five minutes and then ask
whether it changed. The badge of a private repository is seen only by the
collaborators of its project, like the repository.

.. _step-variables:

Variables of the templates
--------------------------

The summary of a step and the descriptions of its tasks take these variables,
in their groups. The examples are those of a pull request of
``collective/icalendar``; the page of a step shows its templates with them.


.. list-table:: Pull request
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{pr_title}``
     - The title of the pull request
     - ``Fix the time zones``
   * - ``{pr_number}``
     - The number of the pull request
     - ``42``
   * - ``{pr_url}``
     - The address of the pull request on GitHub
     - ``https://github.com/collective/icalendar/pull/42``

.. list-table:: Badge
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{pr_badge}``
     - The badge of the pull request in Markdown, linked to its page with its
       steps: ``[![]({pr_badge_url})]({pr_steps_url})``, made of the
       addresses of the site, which are not escaped
     - ``[![](https://dashboard.pycal.org/projects/icalendar/pull/42/badge.svg?repository=collective%2Ficalendar)](https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar)``
   * - ``{pr_badge_url}``
     - The address of the badge of the pull request, see
       :ref:`pull-request-badge`
     - ``https://dashboard.pycal.org/projects/icalendar/pull/42/badge.svg?repository=collective%2Ficalendar``
   * - ``{pr_steps_url}``
     - The address of the page of the pull request with its steps on this
       site, see :ref:`pull-request-page`
     - ``https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar``

The addresses always name the repository of the pull request, so they stay the
same when the project gets another repository with a pull request of the same
number.

.. list-table:: Author
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{author_mention}``
     - Who opened the pull request, mentioned
     - ``@niccokunzmann``
   * - ``{author_name}``
     - The GitHub name of who opened it, else their GitHub handle
     - ``Nicco Kunzmann``
   * - ``{author_handle}``
     - The GitHub handle of who opened it
     - ``niccokunzmann``

.. list-table:: Repository
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{repository_name}``
     - The name of the repository
     - ``icalendar``
   * - ``{repository_full_name}``
     - The account and the name of the repository
     - ``collective/icalendar``
   * - ``{repository_owner}``
     - The account of the repository
     - ``collective``

.. list-table:: Project
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{project_name}``
     - The name of the project
     - ``iCalendar``

.. list-table:: Step
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{step_name}``
     - The name of the step
     - ``Review``
   * - ``{step_number}``
     - The place of the step, counted from 1
     - ``2``
   * - ``{step_id}``
     - The id of the step
     - ``7``

The values are text: a title such as ``[click](https://example.org)`` stays
text, and nothing else of a template is evaluated; a name in braces that is not
a variable stays as it is.

.. _project-roles:

Roles in a project
==================

On the tab *Collaborators*, the owners share the project with other people by
their GitHub handle, such as *niccokunzmann*: the field proposes the people who
signed in, by their GitHub handle or GitHub name, such as *Nicco Kunzmann*,
with their avatar. The person must have signed in to the site once. What each role may do:

.. list-table::
   :header-rows: 1

   * - Action
     - Visitor
     - Read
     - Change
     - Own
   * - See a public project
     - yes
     - yes
     - yes
     - yes
   * - See a private project and private repositories
     - no
     - yes
     - yes
     - yes
   * - Change the name, the description and the repositories
     - no
     - no
     - yes
     - yes
   * - Update it from GitHub
     - no
     - no
     - yes
     - yes
   * - Share it, make it public or private, delete it
     - no
     - no
     - no
     - yes

A project always has an owner: the only owner can neither change their role
nor leave until they give another person the role *own*. The administrators of the site (``SITE_ADMINS``) have the rights
of an owner in every project.

The JSON
========

Public projects have their JSON, such as ``/projects.json`` and
``/projects/icalendar.json``, see :doc:`/reference/json`.

.. list-table:: The pages of a project
   :header-rows: 1

   * - Page
     - Address
   * - Overview
     - ``/projects/<address>/``
   * - Pull requests
     - ``/projects/<address>/pull-requests/``
   * - Repositories
     - ``/projects/<address>/repositories/``
   * - Collaborators
     - ``/projects/<address>/collaborators/``
   * - Settings
     - ``/projects/<address>/settings/``
