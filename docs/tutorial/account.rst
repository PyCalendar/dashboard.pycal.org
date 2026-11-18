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
  one is primary, with *Send a link to verify it* for an address that is not
  verified, see below.
- **Preferences**: the language, the colors and the emails, see below.
- **The GitHub App**: *Install the GitHub App* on the repositories of your
  account or of an organization, see :doc:`/how-to/install-app`. *Your
  installations* lists those you installed or changed: whether they have every
  permission, or what they lack with *Accept the permissions on GitHub*, see
  :ref:`new-permissions`.

.. _administrators:

.. _preferences:

Language, colors and emails
===========================

*Language*
   English, Deutsch or Español, or *As the browser*.
*Colors*
   *As the system*, *Light* or *Dark*, or *As the menu*.

*Emails*
   *Email me when an installation of the GitHub App that I installed or
   changed needs more permissions*, on by default.

Press *Save the preferences*. Your choice applies on every device where you
sign in. The language menu (the globe) and the colors menu (the sun and the
moon) at the top change it, too.

Without a choice, the language of your browser decides, and the colors follow
your system; the menus override them in a cookie of the browser, also when you
are not signed in.

.. _email-addresses:

Email addresses
===============

GitHub shares the addresses that it verified; they are verified on the site,
too. On the page *Email addresses* (*Add an address or choose the primary one*
on the page *Account*, or in the menu of your account) you can:

Add an address
   Enter it and press *Add it and send a link to verify it*. The site sends an
   email with a link to the address.
Verify an address
   Open the link of the email and press *Verify*. The link works without
   signing in. *Send a link to verify it* sends a new one; the site sends at
   most one every 3 minutes.
Choose the primary address
   *Make primary* on a verified address. The site sends its emails to the
   primary address; only a verified address can become the primary one.
Remove an address
   *Remove* on an address that is not the primary one: make another one primary
   first.

The site sends emails only when the people who run it set ``EMAIL_HOST``, see
:doc:`/reference/settings`; without it, the emails are written into its log.

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
