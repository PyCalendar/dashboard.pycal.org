===================
Run the site
===================

The site runs as one container: nginx serves the static files and passes the
rest to gunicorn. The image is ``ghcr.io/pycalendar/dashboard.pycal.org``; the
tag ``latest`` follows the branch ``main``, and it is only pushed when all tests
pass.

1. Copy the example settings and the compose file:

   .. code-block:: shell

      curl -O https://raw.githubusercontent.com/PyCalendar/dashboard.pycal.org/main/docker-compose.yml
      curl -o .env https://raw.githubusercontent.com/PyCalendar/dashboard.pycal.org/main/.env.example

2. Edit ``.env``: at least ``SITE_URL``, ``ALLOWED_HOSTS`` and
   ``CSRF_TRUSTED_ORIGINS``. All settings are in :doc:`/reference/settings`.
3. Start it:

   .. code-block:: shell

      docker compose up -d
      docker compose logs dashboard

4. The log says that the site has no GitHub App and no OAuth app yet, and
   shows the setup code:

   .. code-block:: text

      This site has no GitHub App yet. Register it on https://dashboard.pycal.org/setup/github-app/ with the setup code 3f9a-0c41-77d2
      Nobody can sign in: this site has no OAuth app. Enter it on https://dashboard.pycal.org/setup/oauth-app/ with the setup code 3f9a-0c41-77d2

   Set up both as :doc:`github-app` describes, then install the GitHub App,
   see :doc:`install-app`.

The volume ``./data`` holds the SQLite database, the generated secret key and
the credentials of the GitHub App and the OAuth app. Back it up.

The container
=============

At every start, the container migrates the database and says in the log what
is missing (``manage.py prepare``).

The health check of the container calls ``/health/`` with the first host of
``ALLOWED_HOSTS``. While the site starts, nginx answers with a page that says
so.

Update
======

.. code-block:: shell

   docker compose pull && docker compose up -d
