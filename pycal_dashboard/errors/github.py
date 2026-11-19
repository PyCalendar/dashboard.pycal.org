"""Errors of talking to GitHub, of the GitHub App and of signing in."""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class GitHubError(DashboardError):
    """GitHub answered a request of the site with an error.

    The detail shows the request and the answer of GitHub. If it happens again,
    check https://www.githubstatus.com/ and report a bug.
    """

    title = _("GitHub answered with an error")
    status = 502


class GitHubUnreachable(GitHubError):
    """The site could not reach GitHub.

    The network of the site or GitHub is down. Try again in a few minutes. The
    people who run the site check that the container can reach
    ``api.github.com``.
    """

    title = _("GitHub could not be reached")
    status = 503


class GitHubNotFound(GitHubError):
    """GitHub does not know what the site asked for.

    The repository, pull request or installation was deleted, renamed or is
    not visible to the GitHub App.
    """

    title = _("Not found on GitHub")
    status = 404


class GitHubLoginExpired(GitHubError):
    """GitHub did not accept the token of the site.

    The GitHub App was deleted, its private key was revoked, or the clock of
    the server is wrong. Check the settings of the GitHub App and the time of
    the server.
    """

    title = _("GitHub did not accept the token")
    status = 502


class GitHubRateLimited(GitHubError):
    """The site sent too many requests to GitHub.

    GitHub allows a number of requests per hour. Wait until the limit is reset,
    usually within an hour. The dashboard keeps showing what it read before.
    """

    title = _("Too many requests to GitHub")
    status = 503


class GitHubUnavailable(GitHubError):
    """GitHub did not answer in time, or was busy, after the site asked it again.

    GitHub answers 502, 503 or 504 when it is overloaded, or when a query takes too long. The
    site asks again a few times, with smaller pages of GraphQL; the next update tries again.
    If it stays, check https://www.githubstatus.com/.
    """

    title = _("GitHub did not answer in time")
    status = 503


class GitHubQueryFailed(GitHubError):
    """GitHub answered a query of GraphQL with an error.

    The detail shows the type and message of GitHub, such as a field it does not know. If it
    happens again, report a bug: the query of the site does not fit the API of GitHub.
    """

    title = _("GitHub refused the query")


class MissingPermissions(GitHubError):
    """The GitHub App may not do what the site needs.

    An installation lacks a permission that a request of the site needs. An
    owner of the organization accepts the new permissions in the settings of the
    installation on GitHub; :doc:`/reference/permissions` lists them.
    """

    title = _("The GitHub App lacks a permission")
    status = 403
    guide = "reference/permissions.html"
    guide_title = _("Permissions of the GitHub App")


class SignInNotConfigured(GitHubError):
    """Nobody can sign in: the site has no OAuth app.

    People sign in with a separate OAuth app of ``GITHUB_OAUTH_CLIENT_ID`` and
    ``GITHUB_OAUTH_SECRET``. The people who run the site create it on GitHub
    and enter it on ``/setup/oauth-app/``, which the button *Set up signing in*
    of the page of the error opens, with the setup code of the log, as
    :ref:`oauth-app` describes.
    """

    title = _("Signing in is not set up")
    status = 503
    guide = "how-to/github-app.html#oauth-app"
    guide_title = _("The OAuth app for signing in")
    setup = "oauth_app"
    setup_title = _("Set up signing in")


class GitHubAppNotConfigured(GitHubError):
    """The site has no GitHub App yet.

    The site needs its GitHub App to receive the webhooks and to read what GitHub
    knows about the app. Register it on the page *Register the GitHub App*
    (``/setup/github-app/``), which the button of the page of the error opens,
    with the setup code from the log of the site, as :doc:`/how-to/github-app`
    describes.
    """

    title = _("The site has no GitHub App")
    status = 503
    guide = "how-to/github-app.html"
    guide_title = _("Register the GitHub App")
    setup = "register_app"
    setup_title = _("Register the GitHub App")


class InvalidPrivateKey(GitHubError):
    """The private key of the GitHub App cannot sign.

    ``GITHUB_APP_PRIVATE_KEY`` or the file of ``GITHUB_APP_PRIVATE_KEY_FILE``
    is not the PEM key that GitHub generated for the app. Generate a new key in
    the settings of the app on GitHub and set it.
    """

    title = _("The private key of the GitHub App is invalid")
    status = 500
    guide = "how-to/github-app.html"
    guide_title = _("Register the GitHub App")
