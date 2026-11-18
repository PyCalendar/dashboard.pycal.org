===
API
===

The API answers with JSON and needs no sign in. Errors are JSON with ``error``,
``title``, ``detail`` and ``documentation``, see :doc:`errors`. The site keeps
no data of GitHub yet, so the API tells what runs.

``GET /api/v1/``
   ``api`` (the version of the API, ``1``), ``site``, ``version`` and
   ``commit`` of the site, ``github_app`` (whether the GitHub App is
   registered), ``sign_in`` (whether people can sign in),
   ``organizations`` and ``documentation``.

Every other address under ``/api/`` answers with
:class:`~pycal_dashboard.errors.dashboard.ApiEndpointNotFound`.

Example:

.. code-block:: shell

   curl https://dashboard.pycal.org/api/v1/
