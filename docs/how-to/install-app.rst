======================
Install the GitHub App
======================

The GitHub App of the site receives the webhooks of the repositories it is
installed on. It only reads: the site writes nothing to GitHub, such as labels
or comments, and keeps no data of GitHub yet. Installing it is safe for every
repository of the organization.

The app must be registered on the site first, see :doc:`github-app`.

Who can install it
==================

- **Owners of the organization** install the app and choose the repositories.
- **Other members** can ask for it: GitHub sends the request to the owners,
  who approve it in the settings of the organization.
- The app is **private**: only the account that owns it, such as PyCalendar,
  can install it. To install it on other accounts, an owner makes it public in
  the settings of the app on GitHub (*Advanced → Make public*). The site still
  ignores the webhooks of accounts that are not in ``GITHUB_ORGANIZATIONS``,
  see :doc:`/reference/settings`.

All repositories or only some
=============================

GitHub asks where to install the app:

**All repositories**
   Every repository of the organization, also the ones created later.
**Only select repositories**
   The repositories you choose. Add or remove repositories later, see below.

Private repositories are never shown on the site.

The ways to install it
======================

From the site
   Sign in, open the menu of your account and choose **Install the GitHub
   App**, or press **Install the GitHub App** on the page *Account*. GitHub
   asks for the organization and the repositories, then returns to the site,
   which confirms the installation.
After the registration
   The page that confirms the registration of the app has the link *Install
   the app on the repositories*.
From GitHub
   Open the page of the app, ``https://github.com/apps/<slug>``, such as from
   the page *Register the GitHub App* of the site, and press **Install**.
   ``<slug>`` is ``GITHUB_APP_SLUG``.
From the settings of the organization
   *Settings → GitHub Apps* lists the installed apps. **Configure** changes the
   repositories of an installation.

Change or remove the installation
=================================

In the settings of the organization, *Settings → GitHub Apps → Configure*:

- choose *All repositories* or add and remove repositories under *Only select
  repositories*,
- accept new permissions when the app asks for them, see
  :doc:`/reference/permissions`,
- **Suspend** stops the webhooks for a while; **Uninstall** removes the app
  from the organization.

GitHub sends every change as a webhook (``installation`` and
``installation_repositories``); the administrators of the site see them in the
webhook deliveries.
