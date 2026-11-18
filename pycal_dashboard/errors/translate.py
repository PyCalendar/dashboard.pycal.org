"""The translation table: any exception becomes an error people understand."""

import httpx

from .base import DashboardError, UnexpectedError
from .github import GitHubError, GitHubUnreachable


def all_errors() -> dict[str, type[DashboardError]]:
    """Every error class by its name.

    Returns:
        The classes by their names.

    Examples:
        >>> "RepositoryNotFound" in all_errors()
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

    Args:
        error: Any exception.

    Returns:
        The same error, the one it means, or ``UnexpectedError``.

    Examples:
        >>> translate(ValueError("x")).code
        'UnexpectedError'
    """
    if isinstance(error, DashboardError):
        return error
    if isinstance(error, httpx.TransportError):
        return GitHubUnreachable(str(error))
    if isinstance(error, httpx.HTTPError):
        return GitHubError(str(error))
    return UnexpectedError(f"{type(error).__name__}: {error}")
