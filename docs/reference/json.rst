=================
JSON of the pages
=================

Every public page has its information as JSON at the address of the page with
``.json`` instead of the last ``/``. The start page has ``/index.json``.

.. list-table::
   :header-rows: 1

   * - Page
     - JSON
   * - ``/``
     - ``/index.json``: ``site``, ``version`` and ``commit`` of the site,
       ``github_app`` (whether the GitHub App is registered), ``sign_in``
       (whether people can sign in), ``organizations``, ``documentation``
       and ``pages``, the JSON of the other pages
   * - ``/about/``
     - ``/about.json``: ``build`` (version, commit, time of the build) and
       ``github_app`` (its permissions, events and organizations)
   * - ``/licenses/``
     - ``/licenses.json``: ``license`` of the project, the ``licenses`` in
       ``LICENSES/``, the code from other projects (``reused``) and the Python
       ``packages``
   * - ``/projects/``
     - ``/projects.json``: the public ``projects``, each with its ``name``,
       ``slug``, ``description``, ``url`` and public ``repositories``
   * - ``/projects/<slug>/pull-requests/``
     - ``/projects/<slug>/pull-requests.json``: the pull requests of a public
       project, with ``state`` and ``page`` as on the page: each with its
       ``repository``, ``number``, ``title``, ``url``, ``author``, ``status``
       and times
   * - ``/projects/<slug>/``
     - ``/projects/<slug>.json``: a public
       project with its ``open_issues``,
       ``open_pull_requests``, when it was ``updated``, and its
       ``repositories`` with their numbers

The JSON holds what a visitor who is not signed in sees, also when the request
carries the cookie of a session. Pages for signed-in people, such as
``/account/``, have no JSON. Private projects have none.

Read it from other sites
========================

Every answer has the headers of CORS, ``Access-Control-Allow-Origin: *``, so
JavaScript on any site can read it:

.. code-block:: javascript

   const site = "https://dashboard.pycal.org";
   const start = await (await fetch(`${site}/index.json`)).json();
   console.log(start.github_app ? "The GitHub App is registered" : "No GitHub App yet");

Or with ``curl``:

.. code-block:: shell

   curl https://dashboard.pycal.org/index.json

Failures
========

A failure is JSON with ``error``, ``status`` and ``detail``:

``NotFound`` (404)
   The page has no JSON, such as ``/account.json``, or does not exist.
``MethodNotAllowed`` (405)
   The JSON can only be read: ``GET``, ``HEAD`` and ``OPTIONS``.

An error of the site in a page is JSON with ``error``, ``title``, ``detail`` and
``documentation``, the link to its description in :doc:`errors`.
