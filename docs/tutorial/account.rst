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
- **Preferences**: the language and the colors, which the menus at the top
  keep in your browser. The site sends no emails yet; the types of emails to
  switch on and off come with the features that send them.
- **The GitHub App**: *Install the GitHub App* on the repositories of your
  account or of an organization, see :doc:`/how-to/install-app`.

.. _administrators:

Administrators
==============

The people of ``SITE_ADMINS`` get the rights of the Django admin; the rights
follow the setting at every request. The menu of their account has:

*Log*
   What happened to the site and what followed from it: each webhook, each
   sign-in, a change of the rights of an administrator and the setup of the
   apps. Secrets and email addresses are never logged.
*Webhook deliveries*
   The latest 100 webhooks with their outcome and errors.
*Django admin*
   Every table of the site.

Sign out
========

Choose **Sign out** in the menu of your account.
