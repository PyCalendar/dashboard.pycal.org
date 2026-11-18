=========================================
Register the GitHub App and the OAuth app
=========================================

The site has two apps on GitHub with different jobs:

The GitHub App
   Installed on the repositories, it receives their webhooks. It only reads:
   the site writes nothing to GitHub and keeps no data of GitHub yet.
The OAuth app
   Only signs people in. GitHub tells the site who they are and their email
   addresses, read only, and never asks to let the site act on their behalf.

The people who run the site register both through the pages of the site. The
banner *This site has no GitHub App yet* and the page of an error of a missing
app, such as
:class:`~pycal_dashboard.errors.github.SignInNotConfigured`, have a button to
its setup page. At every start, the log says what is missing, with the setup
code:

.. code-block:: text

   This site has no GitHub App yet. Register it on https://dashboard.pycal.org/setup/github-app/ with the setup code 3f9a-0c41-77d2
   Nobody can sign in: this site has no OAuth app. Enter it on https://dashboard.pycal.org/setup/oauth-app/ with the setup code 3f9a-0c41-77d2

The code makes sure that only the people who run the site set up its apps. Show
it again with:

.. code-block:: shell

   docker compose exec dashboard python manage.py github_app_setup_code

With ``DEBUG=true``, such as with ``make run``, no code is needed.

Register the GitHub App on the site
===================================

1. Open ``/setup/github-app/`` on the site, such as
   https://dashboard.pycal.org/setup/github-app/.
2. Enter the name of the app, the organization (``PyCalendar``) and the setup
   code, and press *Register the GitHub App*.
3. Press *Continue to GitHub*. GitHub shows the new app with the permissions of
   :doc:`/reference/permissions`. Press *Create GitHub App*.
4. GitHub returns to the site, which saves the credentials into the volume:
   ``DATA_DIR/.env`` and the private key ``DATA_DIR/github-app.pem``. The site
   uses them at once.
5. Install the app on the repositories, see :doc:`install-app`.

.. _oauth-app:

Sign people in with the OAuth app
=================================

**Required.** Until the site has the OAuth app, nobody can sign in. GitHub has
no manifest for OAuth apps, so it is created by hand:

#. On GitHub, open *Settings → Developer settings → OAuth Apps → New OAuth
   App*, of your account or of the organization.
#. **Homepage URL**: the address of the site, such as
   ``https://dashboard.pycal.org``. **Authorization callback URL**: the address
   of the site plus ``/accounts/github/login/callback/``, such as
   ``https://dashboard.pycal.org/accounts/github/login/callback/``.
#. Register it and generate a client secret.
#. Open ``/setup/oauth-app/`` on the site, also reached from **Sign in**, and
   enter the client ID, the client secret and the setup code. They are kept in
   ``DATA_DIR/.env``. Or set ``GITHUB_OAUTH_CLIENT_ID`` and
   ``GITHUB_OAUTH_SECRET`` in the environment, as in :file:`.env.example`; the
   environment takes precedence.

Afterwards only the administrators of the site (``SITE_ADMINS``) can change the
OAuth app on that page; they need no setup code.

The site never signs people in with the client of the GitHub App
(``GITHUB_CLIENT_ID``): GitHub would ask them to let the site act on their
behalf.

Check the permissions and events
================================

A new version of the site may need more of the app. On *Register the GitHub
App*, the administrators of the site see whether the app has every permission
and event of :doc:`/reference/permissions`, with a link to change them on
GitHub. On the command line:

.. code-block:: shell

   docker compose exec dashboard python manage.py check_app

It fails and names what is missing, such as ``The GitHub App does not receive
the events repository: change them on https://github.com/...``. After the owner
of the app changed the permissions, the owners of the installations accept them
in the settings of the installation.

A site with a local address
===========================

GitHub cannot deliver webhooks to ``http://localhost``. The registration then
creates the app without a webhook; signing in works, but no webhook arrives.
To test webhooks locally, see :doc:`github-app-tunnel`.

Set the app yourself
====================

To use an app that exists, set all of ``GITHUB_APP_ID``, ``GITHUB_APP_SLUG``,
``GITHUB_CLIENT_ID``, ``GITHUB_SECRET``, ``GITHUB_WEBHOOK_SECRET`` and
``GITHUB_APP_PRIVATE_KEY_FILE`` (or ``GITHUB_APP_PRIVATE_KEY``). The settings
of the environment take precedence over those of the registration.
``manage.py app_manifest`` prints the permissions and events the app needs.

One app per site
================

A site has one GitHub App. To change it, remove its ``GITHUB_...`` settings
from the environment and ``DATA_DIR/.env``, delete ``DATA_DIR/github-app.pem``,
restart the site and register again; delete the old app on GitHub.

When it goes wrong
==================

Each error of the registration has a page with details to copy and a link to
its description in :doc:`/reference/errors`, such as
:class:`~pycal_dashboard.errors.registration.SetupCodeWrong`.
