=======================
Register the GitHub App
=======================

The dashboard needs its GitHub App: the app reads the repositories, receives
the webhooks, labels the pull requests and signs people in. Without it, every
page says that the site has no GitHub App yet.

Register it on the site
=======================

1. Find the setup code in the log of the site, or show it:

   .. code-block:: shell

      docker compose exec dashboard python manage.py github_app_setup_code

   The code makes sure that only the people who run the site register its app.
   With ``DEBUG=true``, such as with ``make run``, no code is needed.

2. Open ``/setup/github-app/`` on the site, such as
   https://dashboard.pycal.org/setup/github-app/.
3. Enter the name of the app, the organization (``PyCalendar``) and the setup
   code, and press *Register the GitHub App*.
4. Press *Continue to GitHub*. GitHub shows the new app with the permissions of
   :doc:`/reference/permissions`. Press *Create GitHub App*.
5. GitHub returns to the site, which saves the credentials into the volume:
   ``DATA_DIR/.env`` and the private key ``DATA_DIR/github-app.pem``. The site
   uses them at once.
6. Press *Install the app on the organization* and choose the repositories,
   such as *All repositories*. The site reads them at once and shows what it
   read.

People can sign in now: the site uses the client of the GitHub App for it.

A site with a local address
===========================

GitHub cannot deliver webhooks to ``http://localhost``. The registration then
creates the app without a webhook; signing in and reading the repositories
work, but pull requests are only labeled by ``manage.py sync_repositories``.

Set the app yourself
====================

To use an app that exists, set all of ``GITHUB_APP_ID``, ``GITHUB_APP_SLUG``,
``GITHUB_CLIENT_ID``, ``GITHUB_SECRET``, ``GITHUB_WEBHOOK_SECRET`` and
``GITHUB_APP_PRIVATE_KEY_FILE`` (or ``GITHUB_APP_PRIVATE_KEY``). The settings
of the environment take precedence over those of the registration.
``manage.py app_manifest`` prints the permissions and events the app needs.

Sign in with an OAuth app instead
=================================

The client of a GitHub App shows "act on your behalf" when people sign in,
although the dashboard never does. To avoid it, create an OAuth app on GitHub
with the callback URL ``<SITE_URL>/accounts/github/login/callback/`` and set
``GITHUB_OAUTH_CLIENT_ID`` and ``GITHUB_OAUTH_SECRET``.

When it goes wrong
==================

Each error of the registration has a page with details to copy and a link to
its description in :doc:`/reference/errors`, such as
:class:`~pycal_dashboard.errors.registration.SetupCodeWrong`.
