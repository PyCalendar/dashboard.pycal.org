============
Your account
============

Signing in is optional. It adds a private page, *Account*, with your email
addresses and preferences, and the button to install the GitHub App.

Sign in
=======

1. Press **Sign in with GitHub** at the top.
2. GitHub asks whether the dashboard may know who you are and read your email
   addresses. Accept.
3. You return to the site.

There are no passwords on the dashboard. The site signs people in with an
OAuth app: it stores no token of yours and never writes anything to GitHub on
your behalf.

The page Account
================

Only you see it. It shows:

- **Email addresses**: those GitHub shared, whether they are verified and which
  one is primary. *Add, verify or change email addresses* adds another one,
  which the dashboard verifies with a link.
- **Preferences**: *Email me about my account and news of the site*, on by
  default. The site only writes to verified addresses.
- **The GitHub App**: *Install the GitHub App* on the repositories of an
  organization, see :doc:`/how-to/install-app`.

.. _administrators:

Administrators
==============

The people of ``SITE_ADMINS`` get the rights of the Django admin; the rights
follow the setting at every request. The menu of their account has:

*Log*
   What happened to the site and what followed from it: each webhook, each
   sign-in, a change of the rights of an administrator, the setup of the apps
   and saved preferences. Secrets and email addresses are never logged.
*Webhook deliveries*
   The latest 100 webhooks with their outcome and errors.
*Django admin*
   Every table of the site.

Sign out
========

Choose **Sign out** in the menu of your account.
