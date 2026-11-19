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
- the **description**: what the project is about,
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

The overview and the update
===========================

The overview of a project shows the number of open issues and open pull
requests of all its repositories and of each one, and when it was last
updated, in your time zone.

When repositories are added, the site updates them from GitHub in the
background at once. **Update** updates them again. A progress bar shows how many
are updated; the page reloads itself until the update ends. The project is *up
to date* when every repository was updated in the last day without an error. A
repository that could not be updated shows why.

The site reads a repository with the token of the GitHub App when the app is
installed on it, else without a token, which works for public repositories.
An update reads all issues and pull requests, open and closed: their title,
description, times, and who created them. The first update reads them all;
the next ones read only those that changed.

With the GitHub App installed, activity on GitHub, such as a new pull request
or a comment, updates its repository in the background: the webhook of GitHub
tells the site.

.. _project-pull-requests:

Pull requests
=============

The tab *Pull requests*, public like the project, lists the pull requests of
all its repositories together, the newest first, with the avatar and GitHub
name of who created them. It shows all of them, or only the open, merged or
closed ones. The tile with the number of open pull requests on the overview
leads there.

The tabs of a project are always in this order: the overview, the public tabs,
then those of the collaborators.

.. _project-roles:

Roles in a project
==================

On the tab *Collaborators*, the owners share the project with other people by
their GitHub name, the name of their account on GitHub: the field proposes the
people who signed in, with their avatar and name. The person must have
signed in to the site once. A project always has an owner: the only owner can
neither change their role nor leave until they share the project with another
owner.

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

A project always has an owner: give another person the role *own* before you
give up yours. The administrators of the site (``SITE_ADMINS``) have the rights
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
