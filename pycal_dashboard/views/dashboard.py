"""The public pages of the dashboard: repositories, contributing, reviews, contributors."""

from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render

from pycal_dashboard.errors import InvalidPageNumber, RepositoryNotFound
from pycal_dashboard.models import Profile
from pycal_dashboard.services.contributor_stats import ContributorStats
from pycal_dashboard.services.overview import Overview
from pycal_dashboard.services.request_filters import RequestFilters

PER_PAGE = 50


def page_of(request, items):
    """One page of a long list.

    Args:
        request: The request, with ``page``.
        items: The list.

    Returns:
        The page of Django's paginator.

    Raises:
        InvalidPageNumber: The page does not exist.
    """
    number = RequestFilters(request.GET).page()
    paginator = Paginator(items, PER_PAGE)
    if number > paginator.num_pages:
        raise InvalidPageNumber(f"page={number}; the last page is {paginator.num_pages}")
    return paginator.page(number)


def shows_drafts(user) -> bool:
    """Whether the lists show draft pull requests: the preference of the person, else yes.

    Args:
        user: The visitor.

    Returns:
        False if the person chose not to see drafts.
    """
    if not user.is_authenticated:
        return True
    profile = Profile.objects.filter(user=user).first()
    return profile is None or profile.show_drafts


def find_repository(owner: str, repo: str):
    """A repository that the dashboard shows.

    Args:
        owner: The organization.
        repo: The name.

    Returns:
        The repository.

    Raises:
        RepositoryNotFound: Unknown or private.
    """
    found = Overview.public().filter(full_name__iexact=f"{owner}/{repo}").first()
    if found is None:
        raise RepositoryNotFound(f"{owner}/{repo}")
    return found


def repositories(request):
    """All repositories with their numbers.

    Args:
        request: The request; ``days`` sets the period of the merged pull requests.

    Returns:
        The page.
    """
    days = RequestFilters(request.GET).days()
    return render(
        request,
        "pycal_dashboard/repositories.html",
        {"rows": Overview(days).per_repository(), "days": days},
    )


def repository(request, owner: str, repo: str):
    """One repository: its open issues and pull requests.

    Args:
        request: The request; ``state`` (open or closed) and ``kind`` (all, pulls, issues).
        owner: The organization.
        repo: The name.

    Returns:
        The page.
    """
    found = find_repository(owner, repo)
    filters = RequestFilters(request.GET)
    state = filters.choice("state", ("open", "closed"), "open")
    kind = filters.choice("kind", ("all", "pulls", "issues"), "all")
    days = filters.days()
    overview = Overview(days, Overview.public().filter(pk=found.pk))
    items = overview.items().filter(state=state)
    if kind != "all":
        items = items.filter(is_pull=kind == "pulls")
    if not shows_drafts(request.user):
        items = items.exclude(draft=True)
    return render(
        request,
        "pycal_dashboard/repository.html",
        {
            "repository": found,
            "counts": overview.counts(),
            "page": page_of(request, items.order_by("-updated_at")),
            "state": state,
            "kind": kind,
            "days": days,
        },
    )


def contribute(request):
    """Where newcomers start: issues for newcomers and issues without an answer.

    Args:
        request: The request.

    Returns:
        The page.
    """
    overview = Overview()
    return render(
        request,
        "pycal_dashboard/contribute.html",
        {"starter": overview.starter_issues(), "unanswered": overview.unanswered()[:30]},
    )


def reviews(request):
    """Pull requests that wait for a review, and those without activity for long.

    Args:
        request: The request.

    Returns:
        The page.
    """
    overview = Overview()
    return render(
        request,
        "pycal_dashboard/reviews.html",
        {
            "waiting": overview.waiting_for_review(),
            "stale": overview.stale(),
            "stale_days": settings.STALE_DAYS,
        },
    )


def contributors(request):
    """The people who contributed in the period.

    Args:
        request: The request; ``days`` sets the period.

    Returns:
        The page.
    """
    days = RequestFilters(request.GET).days()
    return render(
        request,
        "pycal_dashboard/contributors.html",
        {"rows": Overview(days).contributors(), "days": days},
    )


def contributor(request, login: str):
    """The public activity of one person.

    Args:
        request: The request.
        login: The GitHub handle.

    Returns:
        The page.
    """
    stats = ContributorStats(login)
    return render(
        request,
        "pycal_dashboard/contributor.html",
        {
            "login": stats.login,
            "numbers": stats.numbers(),
            "open_pulls": stats.open_pulls(),
            "review_requests": stats.review_requests(),
            "recent": stats.recent(),
        },
    )
