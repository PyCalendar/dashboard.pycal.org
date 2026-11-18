==========================================
Test the GitHub App locally with Tailscale
==========================================

A site on ``http://localhost:5000`` can sign people in, because GitHub sends
the browser back to it. Webhooks are different: GitHub's servers deliver them,
and they cannot reach your computer.

This guide makes the local site reachable on the internet with
`Tailscale Funnel <https://tailscale.com/kb/1223/funnel>`_, then registers a
development GitHub App for that address. Everything else stays local: the
database, ``.env`` and the private key.

.. note::

   ``tailscale serve`` only exposes the site to the devices of your tailnet.
   GitHub is not part of it, so use ``tailscale funnel``. Funnel makes the site
   public: anyone with the address can open it. Stop it when you are done.

1. Prepare Tailscale
====================

#. `Install Tailscale <https://tailscale.com/download>`_ on the computer that
   runs ``make run`` and sign in with ``tailscale up``.
#. In the `admin console <https://login.tailscale.com/admin>`_ of the tailnet,
   enable **MagicDNS** and **HTTPS certificates** (DNS page). Funnel needs
   both.
#. Allow Funnel for the computer. ``tailscale funnel`` shows a link to enable
   it when the tailnet policy does not allow it yet.

2. Expose the site
==================

Start the tunnel to the port of ``make run`` in the background:

.. code-block:: shell

   tailscale funnel --bg 5000

The command prints the public address, such as
``https://laptop.tail1234.ts.net``. ``tailscale funnel status`` shows it again.

3. Configure the site for the address
=====================================

Put the address into ``.env`` (see :doc:`develop`), without a slash at the
end:

.. code-block:: shell

   SITE_URL=https://laptop.tail1234.ts.net
   SITE_NAME=dashboard-dev-yourname

``CSRF_TRUSTED_ORIGINS`` follows ``SITE_URL``, and the sign-in callback uses
``https``. Restart ``make run`` and open the public address in the browser.

4. Register the apps
====================

#. Open ``/setup/github-app/`` on the public address and register a
   development GitHub App of its own, never the app of a deployed site: its
   webhook points to your computer. ``make run`` asks for no setup code.
#. Create a development OAuth app with the callback URL
   ``https://laptop.tail1234.ts.net/accounts/github/login/callback/`` and enter
   it on ``/setup/oauth-app/``, see :ref:`oauth-app`.
#. Sign in and install the app on a test repository, see :doc:`install-app`.

5. Watch the webhooks
=====================

#. Change something in the test repository, such as opening an issue.
#. The page *Webhook deliveries* in the menu of your account lists the
   webhook (your handle must be in ``SITE_ADMINS``).
#. On GitHub, *Settings → Developer settings → GitHub Apps → your app →
   Advanced → Recent Deliveries* shows the answer of the site. **Redeliver**
   sends a webhook again.

A ``401`` with
:class:`~pycal_dashboard.errors.webhooks.WebhookSignatureInvalid` means that
the webhook secret of the app and ``GITHUB_WEBHOOK_SECRET`` differ. A delivery
that never reaches ``make run`` means that the tunnel is down: check
``tailscale funnel status``.

6. Stop the tunnel
==================

.. code-block:: shell

   tailscale funnel reset

The site is private again. The address of the computer stays the same, so the
app and ``.env`` keep working the next time.
