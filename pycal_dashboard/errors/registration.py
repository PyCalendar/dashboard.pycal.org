"""Errors of registering the GitHub App on the site, met by the people who run it.

The site registers its own GitHub App on ``/setup/github-app/``, see
:doc:`/how-to/github-app`. Each page of an error has details to copy for a bug
report.
"""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class RegistrationError(DashboardError):
    """A step of registering the GitHub App of the dashboard failed.

    Resolve:
        - Start again on the page *Register the GitHub App* of the dashboard
          (``/setup/github-app/``), as :doc:`/how-to/github-app` describes.
        - When it fails again, copy the details of the page into a bug report, see
          :doc:`/how-to/report-bug`.
    """

    title = _("The GitHub App could not be registered")
    guide = "how-to/github-app.html"
    guide_title = _("Register the GitHub App")


class AppAlreadyRegistered(RegistrationError):
    """The dashboard already has a GitHub App, and a dashboard has only one.

    Resolve:
        - When the app of the dashboard is the one you want, there is nothing to do.
        - To use another app, remove the ``GITHUB_...`` settings from the environment and from
          ``DATA_DIR/.env``, restart the dashboard and register again.

    Context:
        The settings of the app come from the environment or from ``DATA_DIR/.env``, which the
        registration wrote. The detail says which: ``environment`` or ``volume``.
    """

    title = _("The site already has a GitHub App")
    status = 409


class PrivateKeyFileExists(RegistrationError):
    """The file for the private key of the new app exists already.

    Resolve:
        - When the file is the key of another app that you want to use, set the ``GITHUB_...``
          settings of that app.
        - Otherwise, move the file away and register again.

    Context:
        The registration writes the key to ``GITHUB_APP_PRIVATE_KEY_FILE`` or to
        ``DATA_DIR/github-app.pem`` and never overwrites a file. A file there is the key of
        another app.

    Note:
        The detail names the file.
    """

    title = _("A private key exists already")
    status = 409


class AppSettingsInEnvironment(RegistrationError):
    """Settings of a GitHub App are set in the environment, where they override the registration.

    Resolve:
        - To register a new app, remove the settings that the detail names, or leave them empty,
          restart the dashboard and register again.
        - To use an app that exists, set all of its settings instead of registering one.

    Context:
        The settings of the environment take precedence over those that the registration
        writes, so the dashboard would mix two apps. The settings are ``GITHUB_APP_ID``,
        ``GITHUB_APP_SLUG``, ``GITHUB_CLIENT_ID``, ``GITHUB_SECRET``, ``GITHUB_WEBHOOK_SECRET``
        and ``GITHUB_APP_PRIVATE_KEY``.
    """

    title = _("Settings of a GitHub App are set in the environment")
    status = 409


class SetupCodeWrong(RegistrationError):
    """The setup code that you entered is missing or not that of the dashboard.

    Resolve:
        Enter the setup code from the log of the dashboard. ``manage.py github_app_setup_code``
        shows it, too, such as with
        ``docker compose exec dashboard python manage.py github_app_setup_code``.

    Context:
        Only the people who run the dashboard may register its GitHub App. The dashboard writes
        the setup code into its log at every start while it has no app.
    """

    title = _("The setup code is wrong")
    status = 403


class InvalidAppName(RegistrationError):
    """The name of the GitHub App is empty or longer than the 34 characters that GitHub allows.

    Resolve:
        Enter a name of at most 34 characters that no other GitHub App has, such as
        ``dashboard-pycal-org``.
    """

    title = _("The name of the GitHub App is invalid")


class InvalidOrganization(RegistrationError):
    """The organization that you entered is not a GitHub login.

    Resolve:
        - To register the app on an organization, enter the login of the organization, such as
          ``PyCalendar``.
        - To register the app on your own account, leave the field empty.
    """

    title = _("The organization is invalid")


class RegistrationExpired(RegistrationError):
    """The return from GitHub does not belong to a registration that this browser started.

    This happens when:

    - the registration was started in another browser,
    - the session expired, or
    - the page was opened twice.

    Resolve:
        Start the registration again on the page *Register the GitHub App*
        (``/setup/github-app/``).

    Context:
        The dashboard gives each registration a secret state and checks it when GitHub returns.
        It was missing or different.
    """

    title = _("The registration does not belong to this browser")


class RegistrationCodeMissing(RegistrationError):
    """GitHub returned without the code of the new app: the registration was cancelled on GitHub.

    Resolve:
        Start the registration again on the page *Register the GitHub App*
        (``/setup/github-app/``).

    Context:
        GitHub adds ``code`` to the address when it created the app.
    """

    title = _("GitHub returned without a code")


class ManifestConversionFailed(RegistrationError):
    """GitHub refused to hand out the credentials of the new app for the code of the return.

    Resolve:
        - When the app was created on GitHub, delete it there first.
        - Start the registration again on the page *Register the GitHub App*
          (``/setup/github-app/``).

    Context:
        The code of the return is valid for one hour and only once.

    Note:
        The detail shows the answer of GitHub.
    """

    title = _("GitHub refused the code of the new app")
    status = 502


class RegistrationNotSaved(RegistrationError):
    """The credentials of the new app could not be written into the data directory.

    Resolve:
        - Make ``DATA_DIR``, the volume of the container, writable for the user of the container.
        - Then delete the app on GitHub and register again; or generate a new private key in the
          settings of the app on GitHub and set the ``GITHUB_...`` settings yourself.

    Context:
        The dashboard writes the credentials into ``DATA_DIR``. The app exists on GitHub already.

    Note:
        The detail names the directory and the error of the system.
    """

    title = _("The GitHub App could not be saved")
    status = 500
