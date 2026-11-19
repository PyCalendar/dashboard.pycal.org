"""The saved filters of the pull requests of a project: the tab Filters and the page that saves.

A filter keeps the columns of conditions of the table of pull requests, in their order, with
whether each shows the pull requests it applies to, those it does not, or both.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from pycal_dashboard.conditions.group.column import Column
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


def summary(columns: list[Column]) -> dict:
    """The columns of a filter in three groups, as the pages of filters show them.

    Parameters:
        columns: The columns, in their order.

    Returns:
        Each column with its ``index`` and its ``opposite`` if it has one for sure, in
        ``both``: those that show all pull requests, and do not filter; ``not``: those that
        show only the pull requests they do not apply to; ``applies``: those that show only
        those they apply to.
    """
    items = [
        {"column": column, "index": index, "opposite": column.opposite()}
        for index, column in enumerate(columns)
    ]
    return {
        "both": [item for item in items if item["column"].filter == "all"],
        "not": [item for item in items if item["column"].filter == "not"],
        "applies": [item for item in items if item["column"].filter == "applies"],
    }


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
    """The saved filters of a project, each with how many pull requests it shows.

    Parameters:
        request: The request.
        slug: The project.

    Returns:
        The page or its JSON.
    """
    access, moved = opened(request, slug, "filters/")
    if moved:
        return moved
    repositories = shown_repositories(access)
    pulls = pull_requests_of(repositories)
    filters = []
    for saved in access.project.filters.all():
        columns = [Column.decode(value) for value in saved.columns]
        filters.append(
            {
                "saved": saved,
                "columns": columns,
                "summary": summary(columns),
                "count": len(condition_rows(pulls, columns)),
                "path": access.project.path("pull-requests/")
                + table_address(columns, PER_PAGE, saved.pk),
            }
        )
    labels = Label.objects.filter(repository__in=repositories)
    return page(
        request,
        "pycal_dashboard/project_filters.html",
        {
            "project": access.project,
            "access": access,
            "filters": filters,
            "label_colors": {label.name.lower(): label.color for label in labels},
            "tab": "filters",
        },
        lambda: {
            "filters": [filter_data(f["saved"], f["count"], f["path"]) for f in filters],
        },
    )


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
            "count": len(condition_rows(pull_requests_of(repositories), columns)),
            "back": access.project.path("pull-requests/")
            + table_address(columns, PER_PAGE, saved.pk if saved else None),
            "address": table_address(columns, PER_PAGE, saved.pk if saved else None),
            "label_colors": {label.name.lower(): label.color for label in labels},
            "tab": "filters",
        },
    )
