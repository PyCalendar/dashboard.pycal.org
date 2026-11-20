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
is missing (``manage.py prepare``). Then it reads the installations of the
GitHub App and emails people whose installation lacks permissions
(``manage.py check_installations``).

The health check of the container calls ``/health/`` with the first host of
``ALLOWED_HOSTS``. While the site starts, nginx answers with a page that says
so. With JavaScript, the page asks ``/health/`` every three seconds and then
opens the page again with GET: a form sent during the start is not sent again,
and a page that only takes a form (405) leads back to the page of the form.
Without JavaScript, the page reloads itself every 10 seconds.

.. _background:

Background work
===============

What takes long runs in the background, as in community-insights: the webhooks
of GitHub, the updates of the repositories, and what follows them, such as the
comments of the message, the labels of steps and the results of the columns.
The web process only records a webhook and answers GitHub at once, so pages
never wait for this work, also during many deliveries. ``FETCH_WORKER`` says
where it runs:

``external-http-container``
   The default of the image: ``manage.py fetch_worker`` runs as a process of
   its own in the container, next to gunicorn. When it stops, such as out of
   memory, it is started again after 5 seconds. It looks at the queues every
   2 seconds, checks the installations of the GitHub App when it starts, and
   renews every hour what no webhook tells of.
``external-separate-container``
   Only the ``worker`` service of ``docker-compose.yml`` runs it: remove the
   comments of that service. The web container runs none.
``internal``
   A thread of gunicorn, the default outside the image, such as with ``make
   run``.

Both processes share the cache, files in ``/app/data/cache``: the results that
the background prepares after an update make the pages fast.

.. _memory:

Memory
------

The site needs little memory when it is idle, about 60 MB: one process of
nginx and one of gunicorn with four threads (``WORKERS``, ``THREADS``). It
loads what speaks with GitHub only when it does, and the image reads the
licenses of the packages when it is built, into ``licenses.json``. After about
1000 requests gunicorn replaces its process, which gives back the memory that a
busy time took. For many visitors, raise ``WORKERS``; each process needs about
60 MB more. The packages loaded when needed go through an import guard, so that
the threads cannot stop each other while they import them.

Update
======

.. code-block:: shell

   docker compose pull && docker compose up -d

Deploy with Sencho
==================

CI deploys every push of ``main`` after the image was pushed: it asks
`Sencho <https://sencho.pycal.org>`_ to update the stack, then checks the live
site. The job *Deploy to Sencho* fails until the deployment exists:

#. Create the stack in Sencho, named ``dashboard-pycal``, with
   ``docker-compose.yml``, its ``.env`` and the volume ``./data``.
#. In the repository on GitHub, create the environment ``dashboard.pycal.org``
   (*Settings → Environments*) with the secret ``SENCHO_TOKEN``, a token of the
   API of Sencho. A stack of another name is the repository variable
   ``SENCHO_STACK``.
#. Make the package ``ghcr.io/pycalendar/dashboard.pycal.org`` public, or give
   Sencho access to it.

Sencho answers ``409`` while the stack deploys already and ``5xx`` for passing
errors: the job tries ten times, 30 seconds apart.

Check the live site
===================

After each deployment, the job *Check the live site* runs:

.. code-block:: shell

   make check-live                                     # https://dashboard.pycal.org
   LIVE_URL=https://dashboard.example.org make check-live

It waits while the site starts (up to ``LIVE_WAIT`` seconds, 600 by default),
follows the links of the public pages as a visitor, reads their JSON and checks
that errors get their pages: a missing page is 404, not 500, the account asks to
sign in and the webhook refuses unsigned deliveries. It sends nothing but one
unsigned webhook, which the site refuses and logs.
