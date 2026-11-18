======
Errors
======

Every error of the dashboard has its own entry here. The page of an error
shows its title, what happened and a button *What this error means and how to
solve it*, which leads to its entry. Each entry gives:

- the **title** and the **HTTP status** of the page,
- in its first sentence, **why the error appears**,
- after it, **how to resolve it**.

The JSON of the pages and the webhooks answer errors as JSON with the same name,
title and link:

.. code-block:: json

   {
     "error": "WebhookSignatureMissing",
     "title": "The webhook has no signature",
     "detail": "X-Hub-Signature-256",
     "documentation": "https://docs.dashboard.pycal.org/reference/errors.html#pycal_dashboard.errors.webhooks.WebhookSignatureMissing"
   }

An error the site does not know is shown as
:class:`~pycal_dashboard.errors.base.UnexpectedError`: please report it, see
:doc:`/how-to/report-bug`.

Pages of HTTP errors
====================

Pages that do not exist (404), pages a visitor may not open (403), requests
the site cannot understand (400), forms sent without the cookie of the site or
left open too long (403) and failures of the site (500) have pages in the
design of the site. Each shows the status, what happened, what to do, a link
back to the start and one to report a bug. If the page of a failure cannot be
shown with the menu, it is shown without the menu in the same colors; if even
that fails, as plain text.

Pages and API
=============

.. automodule:: pycal_dashboard.errors.dashboard
   :members:
   :show-inheritance:

Account
=======

.. automodule:: pycal_dashboard.errors.account
   :members:
   :show-inheritance:

Registering the GitHub App
==========================

.. automodule:: pycal_dashboard.errors.registration
   :members:
   :show-inheritance:

GitHub
======

.. automodule:: pycal_dashboard.errors.github
   :members:
   :show-inheritance:

Webhooks
========

.. automodule:: pycal_dashboard.errors.webhooks
   :members:
   :show-inheritance:

Settings of the site
====================

.. automodule:: pycal_dashboard.errors.configuration
   :members:
   :show-inheritance:

All errors
==========

.. automodule:: pycal_dashboard.errors.base
   :members:
   :show-inheritance:
   :exclude-members: docs_url, guide_url, code, as_json
