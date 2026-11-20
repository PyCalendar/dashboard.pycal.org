"""Where the background work runs: the modes of ``FETCH_WORKER``, as in community-insights.

The background work is what takes long: the webhooks of GitHub, the updates of repositories
and what follows them, such as the comments of the message, the labels of steps and the
results of the columns. In the modes ``external-...`` the web process only records it and
``manage.py fetch_worker`` does it, so that the pages never wait for it.
"""

from django.conf import settings

from pycal_dashboard.errors import UnknownWorkerMode

INTERNAL = "internal"
HTTP_CONTAINER = "external-http-container"
SEPARATE_CONTAINER = "external-separate-container"
INLINE = "inline"

MODES = {
    INTERNAL: "a thread of the web process; the default for development (make run)",
    HTTP_CONTAINER: "a process of its own in the web container; the default of the image",
    SEPARATE_CONTAINER: "the worker service of docker-compose.yml; the web container runs none",
    INLINE: "in the request that brings the work; for the tests",
}


def mode() -> str:
    """The mode of ``FETCH_WORKER``.

    Returns:
        One of :data:`MODES`.

    Raises:
        UnknownWorkerMode: ``FETCH_WORKER`` is something else.
    """
    found = getattr(settings, "FETCH_WORKER", INTERNAL)
    if found not in MODES:
        raise UnknownWorkerMode(f"FETCH_WORKER={found!r}; use one of: {', '.join(MODES)}")
    return found


def external() -> bool:
    """Whether a process of its own does the background work: the web process only records it."""
    return mode() in (HTTP_CONTAINER, SEPARATE_CONTAINER)
