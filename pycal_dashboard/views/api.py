"""The JSON API of the dashboard: the same public data as the pages.

docs/reference/api.rst describes it. Errors are JSON with ``error``, ``title``, ``detail``
and ``documentation``.
"""

from django.http import JsonResponse
from django.urls import reverse

from pycal_dashboard.services.contributor_stats import ContributorStats
from pycal_dashboard.services.overview import Overview
from pycal_dashboard.services.request_filters import RequestFilters

from .dashboard import find_repository, page_of


def item_json(item) -> dict:
    """An issue or pull request.

    Args:
        item: The item.

    Returns:
        Its public fields.
    """
    return {
        "repository": item.repository.full_name,
        "number": item.number,
        "kind": "pull" if item.is_pull else "issue",
        "title": item.title,
        "status": item.status,
        "author": item.author_login,
        "labels": item.labels,
        "comments": item.comments,
        "url": item.html_url,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def repository_json(repository) -> dict:
    """A repository.

    Args:
        repository: The repository.

    Returns:
        Its public fields.
    """
    return {
        "full_name": repository.full_name,
        "description": repository.description,
        "url": repository.html_url,
        "language": repository.language,
        "archived": repository.archived,
        "stars": repository.stars,
        "api": reverse("api_repository", args=[repository.owner, repository.name]),
    }


def index(request):
    """The addresses of the API.

    Args:
        request: The request.

    Returns:
        JSON with the addresses.
    """
    return JsonResponse(
        {
            "version": 1,
            "overview": reverse("api_overview"),
            "repositories": reverse("api_repositories"),
            "starter_issues": reverse("api_starter_issues"),
            "reviews": reverse("api_reviews"),
            "contributors": reverse("api_contributors"),
        }
    )


def overview(request):
    """The numbers of the start page.

    Args:
        request: The request; ``days`` sets the period.

    Returns:
        JSON of the numbers.
    """
    return JsonResponse(Overview(RequestFilters(request.GET).days()).counts())


def repositories(request):
    """The repositories with their numbers.

    Args:
        request: The request; ``days`` sets the period.

    Returns:
        JSON: ``repositories``.
    """
    rows = Overview(RequestFilters(request.GET).days()).per_repository()
    return JsonResponse(
        {"repositories": [{**repository_json(row.pop("repository")), **row} for row in rows]}
    )


def repository(request, owner: str, repo: str):
    """One repository with its issues and pull requests, 50 per page.

    Args:
        request: The request; ``state``, ``kind``, ``days`` and ``page``.
        owner: The organization.
        repo: The name.

    Returns:
        JSON of the repository, its numbers and ``items``.
    """
    found = find_repository(owner, repo)
    filters = RequestFilters(request.GET)
    state = filters.choice("state", ("open", "closed"), "open")
    kind = filters.choice("kind", ("all", "pulls", "issues"), "all")
    overview = Overview(filters.days(), Overview.public().filter(pk=found.pk))
    items = overview.items().filter(state=state).order_by("-updated_at")
    if kind != "all":
        items = items.filter(is_pull=kind == "pulls")
    page = page_of(request, items)
    return JsonResponse(
        {
            **repository_json(found),
            "counts": overview.counts(),
            "page": page.number,
            "pages": page.paginator.num_pages,
            "items": [item_json(item) for item in page],
        }
    )


def starter_issues(request):
    """Open issues for newcomers.

    Args:
        request: The request.

    Returns:
        JSON: ``items``.
    """
    return JsonResponse({"items": [item_json(item) for item in Overview().starter_issues()]})


def reviews(request):
    """Pull requests that wait for a review, the longest waiting first.

    Args:
        request: The request.

    Returns:
        JSON: ``items``.
    """
    return JsonResponse({"items": [item_json(item) for item in Overview().waiting_for_review()]})


def contributors(request):
    """The people who contributed in the period.

    Args:
        request: The request; ``days`` sets the period.

    Returns:
        JSON: ``contributors`` and ``days``.
    """
    days = RequestFilters(request.GET).days()
    return JsonResponse({"days": days, "contributors": Overview(days).contributors()})


def contributor(request, login: str):
    """The public activity of one person.

    Args:
        request: The request.
        login: The GitHub handle.

    Returns:
        JSON of the numbers, the open pull requests and the requested reviews.
    """
    stats = ContributorStats(login)
    numbers = stats.numbers()
    numbers["since"] = numbers["since"].isoformat() if numbers["since"] else None
    return JsonResponse(
        {
            "login": stats.login,
            **numbers,
            "open_pulls": [item_json(item) for item in stats.open_pulls()],
            "review_requests": [item_json(item) for item in stats.review_requests()],
        }
    )
