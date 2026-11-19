======================
Install the GitHub App
======================

The GitHub App of the site receives the webhooks of the repositories it is
installed on, and reads their open issues and pull requests for the projects,
see :doc:`/tutorial/projects`. It may add labels and a comment to pull
requests, for the automation that is designed next; until then the site
writes nothing to GitHub.

The app must be registered on the site first, see :doc:`github-app`.

Who can install it
==================

The app is **public**: every account can install it, an organization or a
person, not only the one that owns it, such as PyCalendar.

- **Owners of an organization** install the app and choose the repositories.
- **Other members** can ask for it: GitHub sends the request to the owners,
  who approve it in the settings of the organization.
- **A person** installs it on the repositories of their own account.

An app registered before it was public stays private: its owner makes it
public in the settings of the app on GitHub (*Advanced → Make public*).

All repositories or only some
=============================

GitHub asks for the account and where to install the app:

**All repositories**
   Every repository of the organization, also the ones created later.
**Only select repositories**
   The repositories you choose. Add or remove repositories later, see below.

A private repository is shown only in private projects, to their collaborators, see
:ref:`private-repositories`.

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

.. _new-permissions:

When the app needs more permissions
===================================

The site records each installation with the permissions its owners accepted:
from the webhooks of the installation, and at every start of the site from
GitHub (``manage.py check_installations``). When a new version of the site
needs a permission that an installation lacks:

- the people who installed or changed the installation, and the writers and
  owners of the projects with a repository of it, get an email, once for each
  set of missing permissions, in their language, with the link to the page on
  GitHub where the permissions are accepted. They switch these emails off on
  their page *Account*;
- their page *Account* lists the installation as *needs more permissions*, with
  the missing permissions and the button *Accept the permissions on GitHub*.

An owner of the account accepts them in the settings of the installation on
GitHub; the webhook ``new_permissions_accepted`` records them. A person gets
the emails only with an account on the site and a verified email address, see
:ref:`email-addresses`.

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
