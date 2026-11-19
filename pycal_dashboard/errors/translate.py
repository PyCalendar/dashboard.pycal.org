"""The translation table: any exception becomes an error people understand."""

import sys

from .base import DashboardError, UnexpectedError
from .github import GitHubError, GitHubUnreachable


def all_errors() -> dict[str, type[DashboardError]]:
    """Every error class by its name.

    Returns:
        The classes by their names.

    Examples:
        >>> "InvalidInstallationId" in all_errors()
        True
    """
    found, todo = {}, [DashboardError]
    while todo:
        cls = todo.pop()
        found[cls.__name__] = cls
        todo.extend(cls.__subclasses__())
    return found


def translate(error: BaseException) -> DashboardError:
    """The error to show for any exception.

    Parameters:
        error: Any exception.

    Returns:
        The same error, the one it means, or ``UnexpectedError``.

    Examples:
        >>> translate(ValueError("x")).code
        'UnexpectedError'
    """
    if isinstance(error, DashboardError):
        return error
    # httpx is loaded only for the requests to GitHub: if it is not loaded, the error is not one
    # of its errors, and the idle site does not keep it in memory
    httpx = sys.modules.get("httpx")
    if httpx and isinstance(error, httpx.TransportError):
        return GitHubUnreachable(str(error))
    if httpx and isinstance(error, httpx.HTTPError):
        return GitHubError(str(error))
    return UnexpectedError(f"{type(error).__name__}: {error}")
