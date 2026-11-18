==================================
Permissions of the GitHub App
==================================

The GitHub App asks for as little as the dashboard needs
(``pycal_dashboard/github/permissions.py``). It only reads: the dashboard
writes nothing to GitHub, such as labels or comments. Automation that writes
is designed later.

Permissions of the repositories
===============================

``metadata``: read
   The repositories of the installation.
``issues``: read
   The webhooks of issues and their comments.
``pull_requests``: read
   The webhooks of pull requests and their reviews.

The app asks nothing of the people who use the site: they sign in with the
OAuth app, which only reads who they are and their email addresses (the scope
``user:email``), see :ref:`oauth-app`.

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
the app was installed or its repositories changed.

The site logs every webhook and does nothing else with it yet.

The app is public: every account can install it, see
:doc:`/how-to/install-app`.
