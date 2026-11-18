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

Tests
=====

.. code-block:: shell

   make test              # unit and API tests, on all processors, with coverage
   make browser-install   # once: Chromium for Playwright
   make browser-test      # browser tests, on all processors
   make lint              # ruff
   make docs              # the documentation; warnings fail

The tests run in parallel with `pytest-xdist
<https://pytest-xdist.readthedocs.io/>`_; ``JOBS=0`` runs them in one process.
They never use the network: GitHub is faked in ``tests/fakes/github.py``.

- ``tests/`` are the unit tests of the services, the webhooks and the pages.
- ``tests/api/`` are the tests of the JSON API.
- ``tests/browser/`` start the site and click through it in Chromium.

The models
==========

After a change of the models:

.. code-block:: shell

   make migrations

``make test`` fails if a migration is missing. Never change a migration that
may be applied somewhere; add a new one.

Continuous integration
======================

Every push runs these jobs in parallel: lint and the tests, the browser tests,
the documentation and the build of the Docker image (with its health check).
The image is pushed to ``ghcr.io`` only when all of them pass.

CI publishes the documentation of ``main`` on GitHub Pages, at
https://docs.dashboard.pycal.org/.
