=======
Develop
=======

You need `uv <https://docs.astral.sh/uv/>`_, ``make`` and ``git``.

.. code-block:: shell

   git clone git@github.com:PyCalendar/dashboard.pycal.org.git
   cd dashboard.pycal.org
   make dev    # Python, packages, git hooks, prompt recording, database
   make run    # http://localhost:5000

``make help`` lists all targets. ``make run`` starts the site with
``DEBUG=true``, so that it registers its GitHub App without a setup code.

Settings for development
========================

``make run`` reads ``.env``. Start from the example for development:

.. code-block:: shell

   cp .env.development.example .env

It names the settings that matter locally: a unique ``SITE_NAME`` for your
development app, the OAuth app for signing in and your handle in
``SITE_ADMINS``. :file:`.env.example` lists every setting.

GitHub cannot deliver webhooks to ``localhost``. To test them, make the site
reachable through a tunnel, see :doc:`github-app-tunnel`.

Tests
=====

.. code-block:: shell

   make test              # unit and API tests, on all processors, with coverage
   make browser-install   # once: Chromium for Playwright
   make browser-test      # browser tests, on all processors
   make lint              # ruff
   make docs              # the documentation; warnings fail
   make prose             # the prose of the documentation (Vale)
   make docker-test       # the image: healthy, with the setup code in the log
   make docker-scan       # the image: no critical vulnerabilities with a fix (Trivy)

The tests run in parallel with `pytest-xdist
<https://pytest-xdist.readthedocs.io/>`_; ``JOBS=0`` runs them in one process.
They never use the network: GitHub is faked in ``tests/fakes/github.py``.

- ``tests/`` are the unit tests of the services, the webhooks and the pages.
- ``tests/test_public_json.py`` tests the JSON of the pages.
- ``tests/browser/`` start the site and click through it in Chromium.

The models
==========

After a change of the models:

.. code-block:: shell

   make migrations

``make test`` fails if a migration is missing. Never change a migration that
may be applied somewhere; add a new one.

When what the site keeps of GitHub changes, such as a new field of the issues,
raise ``DATA_VERSION`` in ``pycal_dashboard/github/data_version.py`` together
with the migration. At the next start, ``manage.py prepare`` queues the updates
of the projects whose repositories were read with an older version, and
``manage.py update_projects`` reads them completely again in the background.
A repository whose update failed keeps its older version and is read
completely at the next update.

Every update takes the same path, whoever starts it: the button *Update*, a
webhook, the hourly ``manage.py update_projects --stale``, an overview that may
be out of date, or the start after a migration. Each queues a job
(``UpdateQueue``), the worker reads GitHub in the background
(``RepositoryUpdate``), and the signals of
``pycal_dashboard/update_signals.py`` tell of the result:
``repository_updated`` and ``project_updated``. What has to follow an update
connects to them in ``pycal_dashboard/receivers.py``, never to a trigger.

A new model or field of data of people also goes into the privacy policy,
``pycal_dashboard/privacy.py``: ``tests/test_privacy.py`` fails until it is
there.

Continuous integration
======================

Every push runs these jobs in parallel: lint and the tests, the browser tests,
the documentation with its prose and the workflows, and the build of the Docker
image with its health check and the scan of Trivy. The image is pushed to
``ghcr.io`` only when all of them pass. For ``main``, Sencho then deploys it and
``make check-live`` checks the live site, see :doc:`run-docker`.

Words that Vale does not know, such as names, go into
``.vale/styles/config/vocabularies/Dashboard/accept.txt``.

CI publishes the documentation of ``main`` on GitHub Pages, at
https://docs.dashboard.pycal.org/.
