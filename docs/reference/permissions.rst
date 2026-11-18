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
   The issues: issues for newcomers and those without an answer.
``pull_requests``: read
   The pull requests: what waits for a review.

Permissions of the people who sign in
=====================================

``email_addresses``: read
   The verified email addresses, for the account page and the emails people
   choose.

Events
======

``issues``, ``issue_comment``
   An issue was opened, changed or commented.
``pull_request``
   A pull request was opened or changed: the dashboard stores it.
``pull_request_review``
   A pull request was reviewed: the requested reviewers changed.
``repository``
   A repository was renamed, archived, made private or deleted.

``installation`` and ``installation_repositories`` come without a subscription:
the dashboard reads an installation when it is created or its repositories
change.

The app is not public: only its owner can install it. The dashboard shows the
accounts of ``GITHUB_ORGANIZATIONS`` only.
