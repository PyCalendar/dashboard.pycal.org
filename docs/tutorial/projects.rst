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
as checks that were never read. See :doc:`/reference/conditions/index`.

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
stays a column of the table without filtering. For a condition that shows only
what it does not apply to, the page suggests its opposite where it is the same,
such as *label absent* for not *label present*; **Use it** switches it.

The tab *Filters*, public like the project, lists the saved filters with their
description; opening one counts the pull requests it shows and those each of its
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
filter, whose conditions are what keeps a pull request in it, such as a
conflict or a missing review: failures to remove before it can be merged. A
pull request is in the left-most step whose filter shows it, and in no step
when none does.

There are no steps until they are made: **Make it a step** next to a filter on
the tab *Filters*, or the button **+** of the tab *Steps*, adds the filter as
the last step. Drag a step in the bar to move it, or use its arrows; steps more
to the left come first.

A click on a step shows it below the bar. Its name is that of its filter until
you change it, and its summary is a template in Markdown. The pencil next to each
condition of the filter edits its summary, a line of text, and its description,
which guides people to remove the condition, such as with a link to the
documentation. The summary and the descriptions take variables, which the menu
next to them inserts: ``{author}``, ``{title}``, ``{number}``, ``{url}``,
``{repository}``, ``{full_name}``, ``{owner}``, ``{project}`` and ``{step}``. Their
values are text: a title such as ``[click](https://example.org)`` stays text, and
nothing else of a template is evaluated. The page shows them with an example
pull request.

.. _project-roles:

Roles in a project
==================

On the tab *Collaborators*, the owners share the project with other people by
their GitHub name, the name of their account on GitHub: the field proposes the
people who signed in, with their avatar and name. The person must have
signed in to the site once. What each role may do:

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
