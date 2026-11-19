==================================
Permissions of the GitHub App
==================================

The GitHub App asks for as little as the dashboard needs
(``pycal_dashboard/github/permissions.py``). It writes only to pull requests:
labels and a comment of the site, for the automation that is designed next.
Until then, the site writes nothing to GitHub.

Permissions of the repositories
===============================

``metadata``: read
   The repositories of the installation, and whether a person may read a
   private one before they add it to a project.
``issues``: read
   The webhooks of issues and their comments; the number of open issues.
``pull_requests``: write
   The webhooks of pull requests and their reviews; the number of open pull
   requests. Write: to add and remove the labels of pull requests, and to
   create and update a comment of the site on a pull request.

The app asks nothing of the people who use the site: they sign in with the
OAuth app, which only reads (see :ref:`oauth-app`):

``user:email``
   Who they are and their email addresses.
``read:org``
   Their organizations, whose repositories they add to projects, see
   :ref:`add-repositories`.

Events
======

``issues``, ``issue_comment``
   An issue was opened, changed or commented.
``pull_request``
   A pull request was opened or changed.
``pull_request_review``
   A pull request was reviewed: the requested reviewers changed.
``repository``
   A repository was renamed, archived, made private or deleted.

``installation`` and ``installation_repositories`` come without a subscription:
the app was installed, suspended, removed, its repositories changed or new
permissions were accepted. The site records the installation with its
permissions and events.

The site logs every webhook. Those of a repository of a project update that
repository in the background, see :ref:`project-update`: every kind of data the
site keeps of GitHub has events that tell of its changes, and the app has the
permissions that GitHub needs to send them
(``DATA_EVENTS`` and ``EVENT_PERMISSIONS``; ``tests/test_permissions.py``
checks them). Every hour, the site also renews the repositories not read in the
last day, for what no event tells of.

New permissions
===============

When a new version of the site adds a permission here, the installations lack
it until their owners accept it. The site tells the people who installed or
changed each installation, and the writers and owners of the projects with a
repository of it, by email and on their page *Account*, see
:ref:`new-permissions`. ``manage.py check_installations`` reads the
installations from GitHub; the container runs it at every start.

The app is public: every account can install it, see
:doc:`/how-to/install-app`.
