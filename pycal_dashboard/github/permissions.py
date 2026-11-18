"""The permissions and events of the GitHub App, and its manifest.

The list is in docs/reference/permissions.rst (tests/test_permissions.py checks it).
"""

# What the site needs from an installation.
REQUIRED = {
    "metadata": "read",  # the repositories of the installation
    "issues": "read",  # the webhooks of issues and their comments
    "pull_requests": "read",  # the webhooks of pull requests and their reviews
}
# The app asks nothing of the people who use it: they sign in with the OAuth app.
# The events the app receives. "installation" and "installation_repositories" come without
# a subscription.
EVENTS = ["issues", "issue_comment", "pull_request", "pull_request_review", "repository"]
LEVELS = {"read": 1, "write": 2, "admin": 3}


def missing(granted: dict[str, str], required: dict[str, str] | None = None) -> dict[str, str]:
    """The permissions an installation needs but was not granted.

    Args:
        granted: The permissions of the installation, as GitHub lists them.
        required: What is needed; :data:`REQUIRED` by default.

    Returns:
        The missing permissions with the level needed.

    Examples:
        >>> missing({"metadata": "read", "issues": "write"}, {"issues": "read"})
        {}
        >>> missing({"pull_requests": "read"}, {"pull_requests": "write"})
        {'pull_requests': 'write'}
    """
    required = REQUIRED if required is None else required
    return {
        name: level
        for name, level in required.items()
        if LEVELS.get(granted.get(name, ""), 0) < LEVELS[level]
    }


def manifest(name: str, url: str, public: bool = True) -> dict:
    """The manifest of the GitHub App, to create it with these permissions and events.

    Args:
        name: The name of the app on GitHub.
        url: The address of the site.
        public: Whether other accounts may install the app; they may by default.

    Returns:
        The manifest, as GitHub reads it.

    Examples:
        >>> manifest("dashboard", "https://dashboard.pycal.org")["hook_attributes"]["url"]
        'https://dashboard.pycal.org/github/webhook/'
        >>> manifest("dashboard", "https://dashboard.pycal.org")["public"]
        True
    """
    return {
        "name": name,
        "url": url,
        "hook_attributes": {"url": f"{url}/github/webhook/", "active": True},
        "redirect_url": f"{url}/setup/github-app/registered/",
        "setup_url": f"{url}/setup/installed/",
        "setup_on_update": True,
        "request_oauth_on_install": False,
        "public": public,
        "default_permissions": dict(REQUIRED),
        "default_events": list(EVENTS),
    }


def describe(permissions: dict[str, str]) -> str:
    """The permissions as text, sorted, such as ``issues:read``.

    Args:
        permissions: The permissions with their levels.

    Returns:
        The text; the same for the same permissions.

    Examples:
        >>> describe({"pull_requests": "read", "issues": "read"})
        'issues:read, pull_requests:read'
    """
    return ", ".join(f"{name}:{level}" for name, level in sorted(permissions.items()))
