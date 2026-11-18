"""Errors of registering the GitHub App on the site, met by the people who run it.

The site registers its own GitHub App on ``/setup/github-app/``, see
:doc:`/how-to/github-app`. Each page of an error has details to copy for a bug
report.
"""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class RegistrationError(DashboardError):
    """The GitHub App could not be registered.

    Start again on the page *Register the GitHub App* of the site, as
    :doc:`/how-to/github-app` describes. If it fails again, copy the details of
    the page into a bug report.
    """

    title = _("The GitHub App could not be registered")
    guide = "how-to/github-app.html"
    guide_title = _("Register the GitHub App")


class AppAlreadyRegistered(RegistrationError):
    """The site already has a GitHub App.

    A site has one GitHub App. Its settings come from the environment or from
    ``DATA_DIR/.env``, which the registration wrote. To use another app, remove
    the ``GITHUB_...`` settings from both and restart the site.
    """

    title = _("The site already has a GitHub App")
    status = 409


class PrivateKeyFileExists(RegistrationError):
    """The file for the private key of the new app exists already.

    The registration writes the key to ``GITHUB_APP_PRIVATE_KEY_FILE`` or to
    ``DATA_DIR/github-app.pem`` and never overwrites a file. A file there is the
    key of another app: set the ``GITHUB_...`` settings of that app, or move the
    file away and register again.
    """

    title = _("A private key exists already")
    status = 409


class AppSettingsInEnvironment(RegistrationError):
    """Settings of a GitHub App are set in the environment.

    The settings of the environment take precedence over those the registration
    writes, so the site would mix two apps. The detail names them. Remove them
    or leave them empty, restart the site and register again; or set all of
    them for an app that exists.
    """

    title = _("Settings of a GitHub App are set in the environment")
    status = 409


class SetupCodeWrong(RegistrationError):
    """The setup code is missing or wrong.

    Only the people who run the site may register its GitHub App. The site
    writes the setup code into its log at every start while it has no app.
    ``manage.py github_app_setup_code`` shows it, such as with
    ``docker compose exec dashboard python manage.py github_app_setup_code``.
    """

    title = _("The setup code is wrong")
    status = 403


class InvalidAppName(RegistrationError):
    """The name of the GitHub App is empty or too long.

    GitHub needs a name of at most 34 characters that no other GitHub App has,
    such as ``dashboard-pycal-org``.
    """

    title = _("The name of the GitHub App is invalid")


class InvalidOrganization(RegistrationError):
    """The organization is not a GitHub login.

    Enter the login of the organization, such as ``PyCalendar``, or leave the
    field empty to register the app on your own account.
    """

    title = _("The organization is invalid")


class RegistrationExpired(RegistrationError):
    """The return from GitHub does not belong to a registration of this browser.

    The site gives each registration a secret state and checks it when GitHub
    returns. It was missing or different: the registration was started in
    another browser, the session expired, or the page was opened twice. Start
    again.
    """

    title = _("The registration does not belong to this browser")


class RegistrationCodeMissing(RegistrationError):
    """GitHub returned without the code of the new app.

    GitHub adds ``code`` to the address when the app was created. Without it,
    the registration was cancelled on GitHub. Start again.
    """

    title = _("GitHub returned without a code")


class ManifestConversionFailed(RegistrationError):
    """GitHub refused to hand out the credentials of the new app.

    The code of the return is valid for one hour and only once. Start again; if
    the app was created on GitHub, delete it there first.
    """

    title = _("GitHub refused the code of the new app")
    status = 502


class RegistrationNotSaved(RegistrationError):
    """The credentials of the new app could not be written into the data directory.

    The site writes them into ``DATA_DIR``, the volume of the container. Make
    the directory writable for the user of the container. The app exists on
    GitHub: delete it there and register again, or generate a new private key
    and set the ``GITHUB_...`` settings yourself.
    """

    title = _("The GitHub App could not be saved")
    status = 500
