========
Settings
========

The site is configured with environment variables, such as in ``.env`` next to
``docker-compose.yml``. ``.env.example`` lists every one of them with its
default. A wrong setting stops the site with an error of :doc:`errors`.

The address
===========

``SITE_URL``
   The address of the site, without ``/`` at the end. The GitHub App, its
   webhook and the sign in use it. Default: ``https://dashboard.pycal.org``.
``SITE_NAME``
   The name in the title bar. Default: ``dashboard.pycal.org``.
``ALLOWED_HOSTS``
   The host names of the site, comma separated. The health check sends the
   first one.
``CSRF_TRUSTED_ORIGINS``
   The addresses whose forms the site accepts, comma separated; forms of other
   origins are refused. Default: ``SITE_URL``.

The GitHub App
==============

Leave these empty and register the app on the site, see
:doc:`/how-to/github-app`; the registration writes them into
``DATA_DIR/.env``. Values of the environment take precedence.

``GITHUB_APP_ID``
   The numeric id of the app.
``GITHUB_APP_SLUG``
   The name of the app in ``https://github.com/apps/<slug>``.
``GITHUB_CLIENT_ID``, ``GITHUB_SECRET``
   The client of the app. The registration stores it; the site does not sign
   people in with it.
``GITHUB_WEBHOOK_SECRET``
   The secret of the webhooks; without it all webhooks are refused.
``GITHUB_APP_PRIVATE_KEY_FILE``
   The file of the private key, such as ``/app/data/github-app.pem``.
``GITHUB_APP_PRIVATE_KEY``
   Or the key itself, with ``\n`` for the line breaks.
``GITHUB_API``
   Only for GitHub Enterprise Server. Default: ``https://api.github.com``.
``GITHUB_ORGANIZATIONS``
   The organizations of the community of the site, comma separated: the start
   page links them, and the form of the registration proposes the first one as
   the owner of the GitHub App. Every account may install the app. Default:
   ``PyCalendar``.

The OAuth app
=============

``GITHUB_OAUTH_CLIENT_ID``, ``GITHUB_OAUTH_SECRET``
   The OAuth app that signs people in; without it nobody can sign in. Enter it
   on ``/setup/oauth-app/``, which writes it into ``DATA_DIR/.env``, or set it
   here, see :ref:`oauth-app`.

People
======

``SITE_ADMINS``
   GitHub handles, comma separated, that administer the site: the Django admin
   and the webhook deliveries. The rights follow the setting at every request,
   also for people who signed in before it changed.
``SIGN_OUT_MINUTES``
   Minutes after signing in when people are signed out again, also while they
   use the site; ``0`` signs nobody out until they sign out themselves.
   Default: ``0``.

Data and secrets
================

``DATA_DIR``
   The directory of the SQLite database, the secret key and the GitHub App.
   Default: ``/app/data`` in the container.
``SECRET_KEY``
   Generated once into ``DATA_DIR`` if empty.
``DATABASE_URL``
   Another database, such as ``postgres://...``; SQLite by default.
``DEBUG``
   ``true`` only for development: details of errors and no setup code.
``LOG_LEVEL``
   ``INFO`` by default.

The container
=============

``PORT``
   The port of nginx in the container. Default: ``5000``.
``WORKERS``, ``THREADS``
   The processes and threads of gunicorn. Default: ``1`` and ``4``. Each process
   keeps the site in memory, threads share it: raise ``WORKERS`` only for many
   visitors, see :ref:`memory`.
``TIMEOUT``
   The seconds a process of gunicorn may be busy before gunicorn replaces it.
   Default: ``120``.
``FETCH_WORKER``
   Where the background work runs: the webhooks of GitHub, the updates of the
   repositories and what follows them, such as the comments of the message.
   ``external-http-container``, the default of the image, runs ``manage.py
   fetch_worker`` as a process of its own in the web container, started again
   when it stops, such as out of memory; ``external-separate-container`` runs
   it only in the ``worker`` service of ``docker-compose.yml``; ``internal``,
   the default outside the image, in a thread of gunicorn; ``inline`` in the
   request, for the tests. The web process then only records the webhooks and
   answers GitHub at once; the log says how long the work after each update
   takes. See :ref:`background`.

Email
=====

``EMAIL_HOST``, ``EMAIL_PORT``, ``EMAIL_HOST_USER``, ``EMAIL_HOST_PASSWORD``, ``EMAIL_USE_TLS``, ``EMAIL_USE_SSL``, ``DEFAULT_FROM_EMAIL``
   The mail server. Without ``EMAIL_HOST`` emails are written into the log.

Look and links
==============

``COLOR_<NAME>``, ``COLOR_DARK_<NAME>``
   The colors of the light and the dark pages, such as ``COLOR_PRIMARY=#2b5b84``.
   The defaults are the colors of sign.pycal.org: the blue ``#3b79aa`` and the
   yellow ``#ffd43b`` of the pycal logo. The names are those of
   ``pycal_dashboard/theme.py``, such as ``PRIMARY``, ``ACCENT`` or ``NAV``.
``FAVICON``
   The icon of the site: an address, such as ``https://pycal.org/favicon.png``,
   or the path of a PNG, ICO or SVG file in the container, such as
   ``/app/data/favicon.png``. Empty: the icon of pycal. A wrong file stops the
   site with :class:`~pycal_dashboard.errors.configuration.FaviconNotFound` or
   :class:`~pycal_dashboard.errors.configuration.UnsupportedFavicon`.
``FOOTER_LINKS``
   The extra links of the footer, comma separated, each ``Title=URL``, such as
   ``pycal.org=https://pycal.org,Blog=https://example.org/blog/``. Empty: no
   extra links. Default: ``pycal.org=https://pycal.org``.
``SOURCE_URL``
   The repository of the code.
``DOCS_URL``
   This documentation; the error pages link to it. Default:
   ``https://docs.dashboard.pycal.org/``.
