"""Errors of talking to GitHub, of the GitHub App and of signing in."""

from .base import DashboardError


class GitHubError(DashboardError):
    """GitHub answered a request of the site with an error.

    The detail shows the request and the answer of GitHub. If it happens again,
    check https://www.githubstatus.com/ and report a bug.
    """

    title = "GitHub answered with an error"
    status = 502


class GitHubUnreachable(GitHubError):
    """The site could not reach GitHub.

    The network of the site or GitHub is down. Try again in a few minutes. The
    people who run the site check that the container can reach
    ``api.github.com``.
    """

    title = "GitHub could not be reached"
    status = 503


class GitHubNotFound(GitHubError):
    """GitHub does not know what the site asked for.

    The repository, pull request or installation was deleted, renamed or is
    not visible to the GitHub App.
    """

    title = "Not found on GitHub"
    status = 404


class GitHubLoginExpired(GitHubError):
    """GitHub did not accept the token of the site.

    The GitHub App was deleted, its private key was revoked, or the clock of
    the server is wrong. Check the settings of the GitHub App and the time of
    the server.
    """

    title = "GitHub did not accept the token"
    status = 502


class GitHubRateLimited(GitHubError):
    """The site sent too many requests to GitHub.

    GitHub allows a number of requests per hour. Wait until the limit is reset,
    usually within an hour. The dashboard keeps showing what it read before.
    """

    title = "Too many requests to GitHub"
    status = 503


class MissingPermissions(GitHubError):
    """The GitHub App may not do what the site needs.

    An installation lacks a permission that a request of the site needs. An
    owner of the organization accepts the new permissions in the settings of the
    installation on GitHub; :doc:`/reference/permissions` lists them.
    """

    title = "The GitHub App lacks a permission"
    status = 403
    guide = "reference/permissions.html"
    guide_title = "Permissions of the GitHub App"


class SignInNotConfigured(GitHubError):
    """Nobody can sign in: the site has no OAuth app.

    People sign in with a separate OAuth app of ``GITHUB_OAUTH_CLIENT_ID`` and
    ``GITHUB_OAUTH_SECRET``. The people who run the site create it on GitHub
    and enter it on ``/setup/oauth-app/`` with the setup code of the log, as
    :ref:`oauth-app` describes.
    """

    title = "Signing in is not set up"
    status = 503
    guide = "how-to/github-app.html#oauth-app"
    guide_title = "The OAuth app for signing in"
