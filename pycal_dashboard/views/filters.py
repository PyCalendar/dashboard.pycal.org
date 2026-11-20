"""The saved filters of the pull requests of a project: the tab Filters and the page that saves.

A filter keeps the columns of conditions of the table of pull requests, in their order, with
whether each shows the pull requests it applies to, those it does not, or both.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.errors import FilterNameMissing, FilterNameTaken
from pycal_dashboard.models import Label, PullRequestFilter

from .json_page import page
from .projects import (
    PER_PAGE,
    condition_rows,
    opened,
    pull_requests_of,
    saved_filter,
    shown_repositories,
    table_address,
)


def summary(columns: list[Column]) -> list[dict]:
    """The conditions of a filter as the pages of filters show them, in their order.

    Parameters:
        columns: The columns of conditions.

    Returns:
        Each column with its ``index``, whether it ``filters`` (a column that shows both the
        pull requests it applies to and those it does not apply to is off), and its
        ``opposite`` if it has one for sure.
    """
    return [
        {
            "column": column,
            "index": index,
            "filters": column.filter != "all",
            "opposite": column.opposite(),
        }
        for index, column in enumerate(columns)
    ]


def switched(columns: list[Column], on: set[int]) -> list[Column]:
    """The columns with the switches of the page of saving: those that are off do not filter.

    A condition that is off becomes a column that shows all pull requests; one that is
    switched on shows those it applies to unless it showed only those it does not apply to.

    Parameters:
        columns: The columns of conditions.
        on: The numbers of the columns whose switch is on.

    Returns:
        The columns.

    Examples:
        >>> from pycal_dashboard.conditions.group.status import StatusGroup
        >>> columns = [Column(StatusGroup, ("open",), "not"), Column(StatusGroup, ("open",))]
        >>> [c.filter for c in switched(columns, {1})]
        ['all', 'applies']
    """
    found = []
    for index, column in enumerate(columns):
        if index not in on:
            filter = "all"
        else:
            filter = column.filter if column.filter != "all" else "applies"
        found.append(Column(column.group, column.choices, filter))
    return found


def filter_data(saved: PullRequestFilter, count: int, path: str) -> dict:
    """The public information of a filter, for the JSON.

    Parameters:
        saved: The filter.
        count: How many pull requests it shows.
        path: The address of the table of pull requests with the filter.

    Returns:
        The data.
    """
    return {
        "name": saved.name,
        "description": saved.description,
        "columns": saved.columns,
        "count": count,
        "pull_requests": path,
        "updated": saved.updated.isoformat(),
    }


@require_http_methods(["GET", "HEAD"])
def project_filters(request: HttpRequest, slug: str):
    """The saved filters of a project; their numbers come when a filter is opened.

    Parameters:
        request: The request.
        slug: The project.

    Returns:
        The page or its JSON, which counts the pull requests of each filter.
    """
    access, moved = opened(request, slug, "filters/")
    if moved:
        return moved
    filters = []
    for saved in access.project.filters.all():
        columns = [Column.decode(value) for value in saved.columns]
        address = table_address(columns, PER_PAGE, saved.pk)
        filters.append(
            {
                "saved": saved,
                "columns": columns,
                "path": access.project.path("pull-requests/") + address,
                "edit": access.project.path("filters/save/") + address,
                "in_force": sum(column.filter != "all" for column in columns),
                "rows": [item for item in summary(columns) if item["filters"]],
                "step": getattr(saved, "step", None) if hasattr(saved, "step") else None,
                "counts": access.project.path(f"filters/{saved.pk}/"),
            }
        )

    def data() -> dict:
        repositories = shown_repositories(access)
        pulls, scope = pull_requests_of(repositories), Scope(repositories)
        return {
            "filters": [
                filter_data(f["saved"], len(condition_rows(pulls, f["columns"], scope)), f["path"])
                for f in filters
            ]
        }

    return page(
        request,
        "pycal_dashboard/project_filters.html",
        {"project": access.project, "access": access, "filters": filters, "tab": "filters"},
        data,
    )


@require_http_methods(["GET", "HEAD"])
def project_filter_counts(request: HttpRequest, slug: str, number: int):
    """How many pull requests a filter shows, and each of its conditions applies to.

    The tab Filters loads it when a filter is opened (``?fragment=1``: the part alone);
    without JavaScript, it is a page of its own.

    Parameters:
        request: The request.
        slug: The project.
        number: The number of the filter.

    Returns:
        The page, or its part.
    """
    access, moved = opened(request, slug, f"filters/{number}/")
    if moved:
        return moved
    saved = saved_filter(access.project, str(number))
    columns = [Column.decode(value) for value in saved.columns]
    repositories = shown_repositories(access)
    scope = Scope(repositories)
    pulls = list(
        pull_requests_of(repositories)
        .select_related("pull_state")
        .prefetch_related("labels", "reviews")
    )
    # only the conditions in force: those that are off are no part of the filter
    rows = [item for item in summary(columns) if item["filters"]]
    for item in rows:
        item["count"] = sum(item["column"].applies(pull, scope) is True for pull in pulls)
    context = {
        "project": access.project,
        "access": access,
        "saved": saved,
        "rows": rows,
        "count": len(condition_rows(pull_requests_of(repositories), columns, scope)),
        "tab": "filters",
    }
    if request.GET.get("numbers"):  # for the table of the tab Filters, which fills them in
        return JsonResponse(
            {"count": context["count"], "conditions": {r["index"]: r["count"] for r in rows}}
        )
    if request.GET.get("fragment"):
        return render(request, "pycal_dashboard/conditions/_counts.html", context)
    return render(request, "pycal_dashboard/project_filter_counts.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def project_filter_save(request: HttpRequest, slug: str):
    """Save the columns of the table of pull requests as a filter, new or under its name.

    The columns come in the address, as the table has them (``col``), with ``saved``, the
    filter that the table shows, if any. The page shows them in three groups and suggests the
    opposite of a column that shows only those it does not apply to, where there is one.

    Parameters:
        request: The request; POST with ``name``, ``description``, the columns and ``save``:
            ``this`` saves the filter that the table showed, ``new`` a new one.
        slug: The project.

    Returns:
        The page, or a redirect to the tab Filters after saving.

    Raises:
        FilterNameMissing: The name is empty.
        FilterNameTaken: Another filter of the project has the name.
    """
    access, moved = opened(request, slug, "filters/save/")
    if moved:
        return moved
    access.require_write()
    form = request.POST if request.method == "POST" else request.GET
    columns = [Column.decode(value) for value in form.getlist("col")]
    saved = saved_filter(access.project, form.get("saved"))
    if "swap" in request.GET:  # a column of crosses for its opposite of check marks
        try:
            index = int(request.GET["swap"])
            columns[index] = columns[index].opposite() or columns[index]
        except (ValueError, IndexError):
            pass
        address = table_address(columns, PER_PAGE, saved.pk if saved else None)
        return redirect(access.project.path("filters/save/") + address)
    if request.method == "POST":
        name = " ".join(request.POST.get("name", "").split())[:100]
        if not name:
            raise FilterNameMissing("")
        on = {int(n) for n in request.POST.getlist("on") if n.isdigit()}
        columns = switched(columns, on)
        target = saved if saved and request.POST.get("save") == "this" else None
        try:
            with transaction.atomic():
                if target is None:
                    target = PullRequestFilter(project=access.project, created_by=request.user)
                target.name = name
                target.description = request.POST.get("description", "")
                target.columns = [column.encode() for column in columns]
                target.save()
        except IntegrityError:
            raise FilterNameTaken(name) from None
        messages.success(request, _("The filter %(name)s is saved.") % {"name": name})
        return redirect(access.project.path("filters/"))
    repositories = shown_repositories(access)
    labels = Label.objects.filter(repository__in=repositories)
    return render(
        request,
        "pycal_dashboard/project_filter_save.html",
        {
            "project": access.project,
            "access": access,
            "columns": columns,
            "summary": summary(columns),
            "saved": saved,
            "count": len(
                condition_rows(pull_requests_of(repositories), columns, Scope(repositories))
            ),
            "back": access.project.path("pull-requests/")
            + table_address(columns, PER_PAGE, saved.pk if saved else None),
            "address": table_address(columns, PER_PAGE, saved.pk if saved else None),
            "label_colors": {label.name.lower(): label.color for label in labels},
            "tab": "filters",
        },
    )
