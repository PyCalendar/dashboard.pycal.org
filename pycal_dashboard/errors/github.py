"""Errors of talking to GitHub, of the GitHub App and of signing in."""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class GitHubError(DashboardError):
    """GitHub answered a request of the dashboard with an error.

    Resolve:
        - When it happens again, check https://www.githubstatus.com/ for a problem of GitHub.
        - When GitHub has none, report a bug with the details, see :doc:`/how-to/report-bug`.

    Note:
        The detail shows the request and the answer of GitHub. The GitHub request in it
        identifies the request at GitHub, such as for its support.
    """

    title = _("GitHub answered with an error")
    status = 502


class GitHubUnreachable(GitHubError):
    """The dashboard could not reach GitHub, because its network or GitHub is down.

    Resolve:
        - Try again in a few minutes.
        - When it stays, the people who run the dashboard check that the container can reach
          ``api.github.com``, or the address of ``GITHUB_API``.
    """

    title = _("GitHub could not be reached")
    status = 503


class GitHubNotFound(GitHubError):
    """GitHub does not know what the dashboard asked for.

    This happens when the repository, pull request or installation:

    - was deleted,
    - was renamed, or
    - is not visible to the GitHub App.

    Resolve:
        - When it was deleted or renamed, check its name on GitHub.
        - When the GitHub App does not see it, install the app on the repository, see
          :doc:`/how-to/install-app`.
    """

    title = _("Not found on GitHub")
    status = 404


class GitHubLoginExpired(GitHubError):
    """GitHub did not accept the token of the dashboard.

    This happens when:

    - the GitHub App was deleted,
    - its private key was revoked, or
    - the clock of the server is wrong.

    Resolve:
        - When the clock of the server is wrong, correct its time.
        - Otherwise, check the settings of the GitHub App on GitHub. When its private key was
          revoked, generate a new one there and set it, as :doc:`/how-to/github-app` describes.

    Context:
        The dashboard signs its token with the private key of the GitHub App, for a few minutes
        from the time of the server.
    """

    title = _("GitHub did not accept the token")
    status = 502


class GitHubRateLimited(GitHubError):
    """The dashboard sent more requests to GitHub than GitHub allows in an hour.

    Resolve:
        Wait until GitHub resets the limit, usually within an hour.

    Context:
        GitHub allows a number of requests per hour. Meanwhile the dashboard keeps showing what
        it read before.
    """

    title = _("Too many requests to GitHub")
    status = 503


class GitHubUnavailable(GitHubError):
    """GitHub did not answer in time, or was busy, also after the dashboard asked it again.

    This happens when:

    - GitHub is overloaded, or
    - a query takes GitHub too long.

    Resolve:
        - Wait: the next update tries again.
        - When it stays, check https://www.githubstatus.com/.

    Context:
        GitHub then answers 502, 503 or 504. The dashboard asks again a few times, with smaller
        pages of GraphQL.
    """

    title = _("GitHub did not answer in time")
    status = 503


class GitHubQueryFailed(GitHubError):
    """GitHub answered a query of GraphQL of the dashboard with an error.

    Resolve:
        When it happens again, report a bug with the details, see :doc:`/how-to/report-bug`.

    Context:
        The query of the dashboard does not fit the API of GitHub, such as with a field that
        GitHub does not know.

    Note:
        The detail shows the type and the message of GitHub.
    """

    title = _("GitHub refused the query")


class MissingPermissions(GitHubError):
    """An installation of the GitHub App lacks a permission that a request of the dashboard needs.

    Resolve:
        An owner of the organization accepts the new permissions in the settings of the
        installation on GitHub. :doc:`/reference/permissions` lists them.
    """

    title = _("The GitHub App lacks a permission")
    status = 403
    guide = "reference/permissions.html"
    guide_title = _("Permissions of the GitHub App")


class SignInNotConfigured(GitHubError):
    """Nobody can sign in, because the dashboard has no OAuth app.

    Resolve:
        The people who run the dashboard create the OAuth app on GitHub, as :ref:`oauth-app`
        describes. Then they enter it, with the setup code of the log, on
        ``/setup/oauth-app/``, which the button *Set up signing in* of the page of the error
        opens.

    Context:
        People sign in with a separate OAuth app, of ``GITHUB_OAUTH_CLIENT_ID`` and
        ``GITHUB_OAUTH_SECRET``, not with the GitHub App.
    """

    title = _("Signing in is not set up")
    status = 503
    guide = "how-to/github-app.html#oauth-app"
    guide_title = _("The OAuth app for signing in")
    setup = "oauth_app"
    setup_title = _("Set up signing in")


class GitHubAppNotConfigured(GitHubError):
    """The dashboard has no GitHub App yet, or no private key of it.

    Resolve:
        - When the dashboard has no app, register it on the page *Register the GitHub App*
          (``/setup/github-app/``), which the button of the page of the error opens, with the
          setup code from the log of the dashboard, as :doc:`/how-to/github-app` describes.
        - When ``GITHUB_APP_ID`` is set, set the private key of the app: the file of
          ``GITHUB_APP_PRIVATE_KEY_FILE``, or ``GITHUB_APP_PRIVATE_KEY``.

    Context:
        The dashboard needs its GitHub App to receive the webhooks and to read what GitHub knows
        about the app.
    """

    title = _("The site has no GitHub App")
    status = 503
    guide = "how-to/github-app.html"
    guide_title = _("Register the GitHub App")
    setup = "register_app"
    setup_title = _("Register the GitHub App")


class InvalidPrivateKey(GitHubError):
    r"""The private key of the GitHub App cannot sign: it is not the PEM key that GitHub generated.

    Resolve:
        Generate a new private key in the settings of the app on GitHub. Save it as the file of
        ``GITHUB_APP_PRIVATE_KEY_FILE``, or set it as ``GITHUB_APP_PRIVATE_KEY``, with ``\n``
        for the line breaks, and restart the dashboard.

    Context:
        ``GITHUB_APP_PRIVATE_KEY`` takes precedence over the file of
        ``GITHUB_APP_PRIVATE_KEY_FILE``.

    Note:
        The detail shows the error of signing.
    """

    title = _("The private key of the GitHub App is invalid")
    status = 500
    guide = "how-to/github-app.html"
    guide_title = _("Register the GitHub App")
