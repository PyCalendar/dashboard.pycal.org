"""The page of one pull request in a project: the steps it goes through and the tasks of each.

The bar at the top shows every step of the project in its order: the complete ones in green
with a check mark, the one the pull request is in chosen, each with a square for each of its
tasks, done in green on the left and to do in red on the right. A click on a step shows its
tasks below: those to do first and open, those done with a check mark and closed.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.http import HttpRequest
from django.views.decorators.http import require_http_methods

from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.errors import PullRequestNotFound
from pycal_dashboard.services.progress import PullRequestProgress
from pycal_dashboard.step_template import expand, values_of

from .json_page import page
from .projects import issue_data, opened, pull_requests_of, shown_repositories


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
    found = list(pull_requests_of(repositories).filter(number=number))
    name = request.GET.get("repository")
    if name:
        found = [issue for issue in found if issue.repository.full_name == name]
    if not found:
        raise PullRequestNotFound(str(number))
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
    progress = PullRequestProgress(issue, access.project, Scope(repositories))
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
