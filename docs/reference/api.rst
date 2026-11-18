===
API
===

The API returns the public data of the pages as JSON. It needs no sign in.
Errors are JSON with ``error``, ``title``, ``detail`` and ``documentation``, see
:doc:`errors`.

``GET /api/v1/``
   The addresses of the API.

``GET /api/v1/overview/?days=90``
   The numbers of the start page: ``repositories``, ``open_issues``,
   ``open_pulls``, ``starter_issues``, ``waiting_for_review``, ``unanswered``,
   ``merged``, ``contributors`` and ``days``.

``GET /api/v1/repositories/?days=90``
   ``repositories``: each with ``full_name``, ``description``, ``url``,
   ``language``, ``archived``, ``stars``, ``api``, ``open_issues``,
   ``open_pulls``, ``waiting`` and ``merged``.

``GET /api/v1/repositories/<owner>/<name>/?state=open&kind=all&page=1``
   One repository, its ``counts`` and 50 ``items`` per page. ``state`` is
   ``open`` or ``closed``; ``kind`` is ``all``, ``pulls`` or ``issues``.

``GET /api/v1/starter-issues/``
   ``items``: open issues for newcomers.

``GET /api/v1/reviews/``
   ``items``: pull requests that wait for a review, the longest waiting first.

``GET /api/v1/contributors/?days=90``
   ``contributors``: ``login``, ``pulls``, ``merged`` and ``issues``.

``GET /api/v1/contributors/<login>/``
   ``login``, ``pulls``, ``merged``, ``issues``, ``repositories``, ``since``,
   ``open_pulls`` and ``review_requests``.

An item has ``repository``, ``number``, ``kind`` (``pull`` or ``issue``),
``title``, ``status`` (``open``, ``draft``, ``merged`` or ``closed``),
``author``, ``labels``, ``comments``, ``url``, ``created_at`` and
``updated_at``.

Example:

.. code-block:: shell

   curl https://dashboard.pycal.org/api/v1/overview/?days=30
