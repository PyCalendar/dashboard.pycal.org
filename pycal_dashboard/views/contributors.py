"""The page of a person in a project: what the states of the author count, with tabs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from pycal_dashboard.conditions.group.author import number_text
from pycal_dashboard.conditions.spec.reviews import COUNTED, STATES
from pycal_dashboard.conditions.state.own_pull_requests_closed import OwnPullRequestsClosed
from pycal_dashboard.conditions.state.pull_requests_opened import PullRequestsOpened
from pycal_dashboard.conditions.state.review_ratio import ReviewRatio
from pycal_dashboard.conditions.state.reviews_given import ReviewsGiven
from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.errors import ContributorNotFound
from pycal_dashboard.models import GitHubUser, Issue, Review

from .projects import opened, shown_repositories

if TYPE_CHECKING:
    from django.http import HttpRequest

TABS = ("profile", "reviews", "issues", "pull-requests")
PER_PAGE = 50


@require_http_methods(["GET", "HEAD"])
def project_contributor(request: HttpRequest, slug: str, login: str):
    """A person of GitHub in a project, public like the project, with tabs.

    *Profile* has the states of the person that conditions compare, such as the review to pull
    request ratio; *Reviews*, *Issues* and *Pull requests* list them with their counts, in the
    repositories of the project that the visitor sees.

    Parameters:
        request: The request; ``tab`` is one of ``TABS``, ``page`` the page of its list.
        slug: The project.
        login: The GitHub handle of the person, in any case.

    Returns:
        The page.

    Raises:
        ContributorNotFound: Nobody of this handle opened an issue or a pull request, or
            reviewed one, in the repositories of the project.
    """
    access, moved = opened(request, slug, f"contributors/{login}/")
    if moved:
        return moved
    repositories = shown_repositories(access)
    issues = Issue.objects.filter(repository__in=repositories, author__login__iexact=login)
    reviews = Review.objects.filter(
        issue__repository__in=repositories, author__login__iexact=login, state__in=COUNTED
    )
    person = (
        GitHubUser.objects.filter(login__iexact=login)
        .filter(Q(pk__in=issues.values("author")) | Q(pk__in=reviews.values("author")))
        .order_by("pk")
        .first()
    )
    if person is None:
        raise ContributorNotFound(login)
    issues = issues.filter(author=person)
    reviews = reviews.filter(author=person)
    tab = request.GET.get("tab", "profile")
    tab = tab if tab in TABS else "profile"
    scope = Scope(repositories)
    counts = {
        "reviews": reviews.count(),
        "issues": issues.filter(pull_request=False).count(),
        "pull_requests": issues.filter(pull_request=True).count(),
    }
    listed = {
        "reviews": reviews.select_related("issue__repository").order_by("-submitted", "-pk"),
        "issues": issues.filter(pull_request=False).select_related("repository"),
        "pull-requests": issues.filter(pull_request=True).select_related("repository"),
    }
    shown = None
    if tab != "profile":
        query = listed[tab]
        if tab != "reviews":
            query = query.order_by("-created", "-pk")
        shown = Paginator(query, PER_PAGE).get_page(request.GET.get("page"))
    return render(
        request,
        "pycal_dashboard/project_contributor.html",
        {
            "project": access.project,
            "access": access,
            "person": person,
            "tab": "contributor",
            "shown_tab": tab,
            "counts": counts,
            "shown": shown,
            "review_states": STATES,
            "states": [
                (ReviewsGiven.title, number_text(ReviewsGiven.measure(person, scope, {}))),
                (
                    PullRequestsOpened.title,
                    number_text(PullRequestsOpened.measure(person, scope, {})),
                ),
                (
                    OwnPullRequestsClosed.title,
                    number_text(OwnPullRequestsClosed.measure(person, scope, {})),
                ),
                (ReviewRatio.title, number_text(ReviewRatio.measure(person, scope, {}))),
            ],
            "multiple": len(repositories) > 1,
        },
    )
