"""The page of one pull request in a project: the steps it goes through and the tasks of each.

The bar at the top shows every step of the project in its order: the complete ones in green
with a check mark, the one the pull request is in chosen, each with a square for each of its
tasks, done in green on the left and to do in red on the right. A click on a step shows its
tasks below: those to do first and open, those done with a check mark and closed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse, HttpResponseNotModified
from django.views.decorators.http import require_http_methods

from pycal_dashboard.errors import PullRequestNotFound, PullRequestNumberAmbiguous
from pycal_dashboard.services.column_results import ColumnResults
from pycal_dashboard.services.progress import PullRequestProgress
from pycal_dashboard.services.pull_request_badge import PullRequestBadge
from pycal_dashboard.step_template import expand, values_of

from .json_page import page
from .projects import issue_data, opened, pull_requests_of, shown_repositories

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, Repository

BADGE_SECONDS = 300  # how long browsers and GitHub keep a badge before they ask again


def numbered(repositories: list[Repository], number: int, name: str | None) -> list[Issue]:
    """The pull requests of a number in the repositories that a person sees.

    Parameters:
        repositories: The repositories of the project that the person sees.
        number: The number of the pull request on GitHub.
        name: The repository, such as ``collective/icalendar``; None for any.

    Returns:
        The pull requests: one, or several of different repositories.

    Raises:
        PullRequestNotFound: None has the number.
    """
    found = list(pull_requests_of(repositories).filter(number=number))
    if name:
        found = [issue for issue in found if issue.repository.full_name == name]
    if not found:
        raise PullRequestNotFound(str(number))
    return found


@require_http_methods(["GET", "HEAD"])
def project_pull_request(request: HttpRequest, slug: str, number: int):
    """The page of a pull request of a project, public like the project.

    Parameters:
        request: The request; ``repository`` chooses among repositories of the project with a
            pull request of the same number, and ``step`` is the step to show.
        slug: The project.
        number: The number of the pull request on GitHub.

    Returns:
        The page or its JSON; a list to choose from when several repositories have a pull
        request of this number.

    Raises:
        PullRequestNotFound: No repository of the project that the person sees has it.
    """
    access, moved = opened(request, slug, f"pull/{number}/")
    if moved:
        return moved
    repositories = shown_repositories(access)
    name = request.GET.get("repository")
    found = numbered(repositories, number, name)
    context = {"project": access.project, "access": access, "tab": "pull-requests"}
    if len(found) > 1:
        choices = [
            (issue, "?" + urlencode({"repository": issue.repository.full_name})) for issue in found
        ]
        return page(
            request,
            "pycal_dashboard/project_pull_request.html",
            {**context, "choices": choices, "number": number},
            lambda: {"pull_requests": [issue_data(issue) for issue, _query in choices]},
        )
    issue = found[0]
    results = ColumnResults(repositories)
    progress = PullRequestProgress(issue, access.project, results.scope, results)
    shown = progress.chosen(request.GET.get("step"))
    keep = {"repository": name} if name else {}
    return page(
        request,
        "pycal_dashboard/project_pull_request.html",
        {
            **context,
            "pull": issue,
            "progress": progress,
            "shown": shown,
            "step_query": "?" + urlencode(keep) + "&step=" if keep else "?step=",
            "step_summary": expand(shown.step.summary, values_of(issue, access.project, shown.step))
            if shown
            else "",
        },
        lambda: {**issue_data(issue), **progress.data()},
    )


@require_http_methods(["GET", "HEAD"])
def project_pull_request_badge(request: HttpRequest, slug: str, number: int, kind: str):
    """The badge of a pull request: the step it is in and its tasks done, such as *Triage 3/4*.

    It is drawn once and cached until the data or the steps change
    (:class:`~pycal_dashboard.services.pull_request_badge.PullRequestBadge`); browsers and
    GitHub keep it for five minutes, and ask again with its ``ETag``.

    Parameters:
        request: The request; ``repository`` names the repository of the pull request.
        slug: The project.
        number: The number of the pull request on GitHub.
        kind: ``svg`` or ``png``.

    Returns:
        The image, or 304 when the browser has it.

    Raises:
        PullRequestNotFound: No repository of the project that the person sees has it.
        PullRequestNumberAmbiguous: Several have it, and the address names none.
    """
    access, moved = opened(request, slug, f"pull/{number}/badge.{kind}")
    if moved:
        return moved
    repositories = shown_repositories(access)
    found = numbered(repositories, number, request.GET.get("repository"))
    if len(found) > 1:
        raise PullRequestNumberAmbiguous(str(number))
    content, media, version = PullRequestBadge(found[0], access.project, repositories).render(kind)
    etag = f'"{version}"'
    private = any(repository.private for repository in repositories)
    answer = (
        HttpResponseNotModified()
        if etag in request.headers.get("If-None-Match", "")
        else HttpResponse(content, content_type=media)
    )
    answer["ETag"] = etag
    answer["Cache-Control"] = f"{'private' if private else 'public'}, max-age={BADGE_SECONDS}"
    return answer
