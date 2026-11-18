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


class GitHubAnswerNotJSON(GitHubError):
    """GitHub answered with something that is not JSON.

    This happens when GitHub has problems, or when ``GITHUB_API`` points to a
    page that is not the API. Check ``GITHUB_API`` and try again.
    """

    title = "GitHub's answer was not JSON"


class MissingPermissions(GitHubError):
    """The GitHub App may not do what the site needs.

    An installation lacks a permission, such as writing the labels of pull
    requests. An owner of the organization accepts the new permissions in the
    settings of the installation on GitHub; :doc:`/reference/permissions` lists
    them.
    """

    title = "The GitHub App lacks a permission"
    status = 403
    guide = "reference/permissions.html"
    guide_title = "Permissions of the GitHub App"


class GitHubAppNotConfigured(GitHubError):
    """The site has no GitHub App yet.

    The site needs its GitHub App to read the repositories and to label pull
    requests. Register it on the page *Register the GitHub App*
    (``/setup/github-app/``) with the setup code from the log of the site, as
    :doc:`/how-to/github-app` describes.
    """

    title = "The site has no GitHub App"
    status = 503
    guide = "how-to/github-app.html"
    guide_title = "Register the GitHub App"


class InvalidPrivateKey(GitHubError):
    """The private key of the GitHub App cannot sign.

    ``GITHUB_APP_PRIVATE_KEY`` or the file of ``GITHUB_APP_PRIVATE_KEY_FILE``
    is not the PEM key that GitHub generated for the app. Generate a new key in
    the settings of the app on GitHub and set it.
    """

    title = "The private key of the GitHub App is invalid"
    status = 500
    guide = "how-to/github-app.html"
    guide_title = "Register the GitHub App"


class InstallationNotFound(GitHubError):
    """The GitHub App is not installed where the site expected it.

    The installation was removed or suspended. Install the app again on the
    organization.
    """

    title = "The GitHub App is not installed"
    status = 404


class InstallationNotAllowed(GitHubError):
    """The GitHub App was installed on an account that this dashboard does not show.

    The dashboard shows the organizations of ``GITHUB_ORGANIZATIONS`` only, such
    as ``PyCalendar``. Install the app there, or add the account to the setting.
    """

    title = "This account is not part of the dashboard"
    status = 403


class SignInNotConfigured(GitHubError):
    """Nobody can sign in: the site has no GitHub client for signing in.

    People sign in with the client of the GitHub App, which the registration
    stores, or with an OAuth app of ``GITHUB_OAUTH_CLIENT_ID`` and
    ``GITHUB_OAUTH_SECRET``. Register the GitHub App first, as
    :doc:`/how-to/github-app` describes.
    """

    title = "Signing in is not set up"
    status = 503
    guide = "how-to/github-app.html"
    guide_title = "Register the GitHub App"
