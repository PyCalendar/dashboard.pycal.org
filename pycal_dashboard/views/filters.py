"""The saved filters of the pull requests of a project: the tab Filters and the page that saves.

A filter keeps the columns of conditions of the table of pull requests, in their order, with
whether each shows the pull requests it applies to, those it does not, or both.
"""

from __future__ import annotations

from dataclasses import replace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse, QueryDict
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from pycal_dashboard.conditions.group.column import OPERATORS, Column
from pycal_dashboard.conditions.group.conjunction import Conjunction
from pycal_dashboard.errors import FilterNameMissing, FilterNameTaken
from pycal_dashboard.models import Label, PullRequestFilter, PullRequestStep
from pycal_dashboard.services.column_results import ColumnResults
from pycal_dashboard.services.project_access import ProjectAccess

from .json_page import page
from .projects import (
    PER_PAGE,
    PER_PAGE_CHOICES,
    opened,
    saved_filter,
    shown_repositories,
    table_address,
)


def summary(columns: list[Column], enabled: bool = False) -> list[dict]:
    """The conditions of a filter as the pages of filters show them, in their order.

    The columns joined by AND come together, in the place of their first one.

    Parameters:
        columns: The columns of conditions.
        enabled: Whether every condition is switched on, as for a filter saved the first
            time; else those that filter.

    Returns:
        Each column with its ``index``, whether it ``filters`` (a column that shows both the
        pull requests it applies to and those it does not apply to is off), and its
        ``opposite`` if it has one for sure; ``joined``, the number of its AND (0 for none),
        with ``first`` and ``last`` of it and the ``conjunction`` at the first; and
        ``above``, whether a condition of its type is above it that it can be joined with.
    """
    found = []
    seen: set[str] = set()  # the types of the conditions above
    for numbers in Conjunction.indices(columns):
        kind = columns[numbers[0]].kind
        number = columns[numbers[0]].joined if len(numbers) > 1 else 0
        for place, index in enumerate(numbers):
            column = columns[index]
            found.append(
                {
                    "column": column,
                    "index": index,
                    "filters": enabled or column.active,
                    "opposite": column.opposite(),
                    "inverted": column.inverted(),
                    "skips": column.kind == "skip",  # its section, also when it is off
                    "joined": number,
                    "first": bool(number) and place == 0,
                    "last": bool(number) and place == len(numbers) - 1,
                    "conjunction": Conjunction(tuple(columns[n] for n in numbers))
                    if number and place == 0
                    else None,
                    "above": kind in seen,
                }
            )
        seen.add(kind)
    return found


def in_force(columns: list[Column]) -> list[dict]:
    """The conditions of a filter that are switched on, as the tab Filters lists them.

    Parameters:
        columns: The columns of conditions.

    Returns:
        Those of :func:`summary` that filter, each with ``and_before``: whether the one before
        it is of its AND.
    """
    rows = [item for item in summary(columns) if item["filters"]]
    for before, item in zip([None, *rows], rows, strict=False):
        item["and_before"] = bool(
            before
            and item["joined"]
            and (before["joined"], before["skips"]) == (item["joined"], item["skips"])
        )
    return rows


def page_size(form: QueryDict) -> int:
    """The size of the table of pull requests that the page of saving goes back to.

    Parameters:
        form: The address or the form sent, with ``per_page``.

    Returns:
        A number of ``PER_PAGE_CHOICES``; the default for another one.

    Examples:
        >>> from django.http import QueryDict
        >>> page_size(QueryDict("per_page=50")), page_size(QueryDict("per_page=7"))
        (50, 25)
    """
    value = form.get("per_page", "")
    return int(value) if value.isdigit() and int(value) in PER_PAGE_CHOICES else PER_PAGE


def typed(column: Column, kind: str) -> Column:
    """A column as a condition of another type, switched on or off as it was, in no AND.

    Parameters:
        column: The column.
        kind: ``skip`` for Skip if, ``check`` for the quality checks.

    Returns:
        The column; the same when it has the type.
    """
    if column.kind == kind:
        return column
    if kind == "skip":  # a condition of Skip if: it applies, the step is skipped
        return replace(column, filter="skip" if column.active else "skip_off", joined=0)
    return replace(column, filter="applies" if column.active else "all", joined=0)


def placed(columns: list[Column], index: int, before: int | None, kind: str) -> list[Column]:
    """The columns with one put between the conditions of a section, out of its AND.

    Parameters:
        columns: The columns of conditions.
        index: The place of the column.
        before: The place of the first column of the condition that it comes before; None for
            the end of the section.
        kind: The type of the section: ``skip`` for Skip if, ``check`` for the quality checks.

    Returns:
        The columns; the same when it is put where it is, alone, such as by a drop where it
        was picked up.

    Examples:
        >>> from pycal_dashboard.conditions.group.status import StatusGroup
        >>> columns = [Column(StatusGroup, (state,), "applies") for state in ("open", "draft")]
        >>> placed(columns, 1, 0, "check") == columns[::-1]
        True
        >>> placed(columns, 0, 1, "check") == columns  # where it was
        True
    """
    if before is not None and not 0 <= before < len(columns):
        return columns
    column = replace(typed(columns[index], kind), joined=0)
    changed = list(columns)
    del changed[index]
    if before is None:
        changed.append(column)
    else:
        changed.insert(before - (before > index), column)
    return changed


def joined(columns: list[Column], index: int, target: int | None) -> list[Column]:
    """The columns with one joined by AND with another one, or with the AND of it.

    It takes the type of the other one, and comes after the last column of the AND.

    Parameters:
        columns: The columns of conditions.
        index: The place of the column to join.
        target: The place of the column to join it with; None for the condition of its type
            above it, as the page shows them.

    Returns:
        The columns.
    """
    if target is None:
        kind = columns[index].kind
        above = [n for n in Conjunction.indices(columns) if columns[n[0]].kind == kind]
        place = next(p for p, numbers in enumerate(above) if index in numbers)
        if place == 0:
            return columns
        target = above[place - 1][-1]
    if not 0 <= target < len(columns) or target == index:
        return columns
    other = columns[target]
    column = columns[index]
    if other.joined and (column.kind, column.joined) == (other.kind, other.joined):
        return columns  # in the AND already
    number = other.joined or max(c.joined for c in columns) + 1
    changed = list(columns)
    changed[target] = replace(other, joined=number)
    del changed[index]
    last = max(p for p, c in enumerate(changed) if (c.kind, c.joined) == (other.kind, number))
    changed.insert(last + 1, replace(typed(column, other.kind), joined=number))
    return changed


def saved_columns(form: QueryDict, columns: list[Column]) -> list[Column] | None:
    """The columns after a button of the page of saving, such as ``invert`` or ``skip``.

    The buttons: ``swap``, ``invert``, ``remove``, ``skip`` (into Skip if), ``check`` (into
    the quality checks), ``join`` (by AND, with the condition of ``to``, else with the one
    above), ``unjoin`` (out of its AND) or ``place`` (before the condition of ``to``, or at
    the end of the ``section``: ``checks`` or ``skip``), or ``operator`` (the radio choices of
    AND and OR, which every form sent applies, see :func:`operated`). An AND of one column is
    none.

    Parameters:
        form: The address or the form sent, with the number of the column of the button.
        columns: The columns of conditions.

    Returns:
        The changed columns; None without such a button.
    """
    actions = ("swap", "invert", "remove", "skip", "check", "join", "unjoin", "place", "operator")
    for action in actions:
        if action not in form:
            continue
        changed = list(columns)
        try:
            index = int(form[action])
            column = changed[index]
            target = int(form["to"]) if action in ("join", "place") and form.get("to") else None
        except (ValueError, IndexError):
            return changed
        if action == "remove":
            del changed[index]
        elif action == "skip":  # a condition of Skip if: it applies, the step is skipped
            changed[index] = typed(column, "skip")
        elif action == "check":  # a quality check: the step waits for it
            changed[index] = typed(column, "check")
        elif action == "join":
            changed = joined(changed, index, target)
        elif action == "unjoin":
            changed[index] = replace(column, joined=0)
        elif action == "place":  # dropped between two conditions, or at the end of a section
            kind = "skip" if form.get("section") == "skip" else "check"
            changed = placed(changed, index, target, kind)
        elif action == "operator":  # the choices of AND and OR are applied already
            pass
        elif action == "invert":
            changed[index] = column.inverted() or column
        else:  # a column of crosses for its opposite of check marks
            changed[index] = column.opposite() or column
        return Conjunction.normalized(changed)
    return None


def operated(columns: list[Column], form: QueryDict) -> list[Column]:
    """The columns with the radio choices of the page of saving: AND or OR for each group.

    The choice of a group is ``operator<index>``, by the place of its first column: ``and`` or
    ``or``. A group without its choice in the form stays as it was.

    Parameters:
        columns: The columns of conditions.
        form: The form sent.

    Returns:
        The columns, each of a group with the operator chosen for it.

    Examples:
        >>> from django.http import QueryDict
        >>> values = ["and1~status~applies~open", "and1~status~applies~draft"]
        >>> found = operated([Column.decode(v) for v in values], QueryDict("operator0=or"))
        >>> [column.encode() for column in found]
        ['or1~status~applies~open', 'or1~status~applies~draft']
    """
    changed = list(columns)
    for numbers in Conjunction.indices(changed):
        operator = form.get(f"operator{numbers[0]}")
        if len(numbers) > 1 and operator in OPERATORS:
            for number in numbers:
                changed[number] = replace(changed[number], operator=operator)
    return changed


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
    return [column.switched(index in on) for index, column in enumerate(columns)]


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
                "in_force": sum(column.active for column in columns),
                "rows": in_force(columns),
                "step": getattr(saved, "step", None) if hasattr(saved, "step") else None,
                "counts": access.project.path(f"filters/{saved.pk}/"),
            }
        )

    def data() -> dict:
        results = ColumnResults(
            shown_repositories(access), project=access.project
        )  # loaded once for all filters
        return {
            "filters": [
                filter_data(f["saved"], len(results.matching(f["columns"])), f["path"])
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
    results = ColumnResults(shown_repositories(access), project=access.project)
    # only the conditions in force: those that are off are no part of the filter
    rows = in_force(columns)
    for item in rows:
        item["count"] = results.count(item["column"])
    context = {
        "project": access.project,
        "access": access,
        "saved": saved,
        "rows": rows,
        "count": len(results.matching(columns)),
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
    The buttons of a condition (such as ``skip``) send the form, which a drop presses, too:
    the page comes again with what was typed. Its first button saves, for Enter.

    Parameters:
        request: The request; POST with ``name``, ``description``, the columns and ``save``:
            ``this`` saves the filter that the table showed, ``new`` a new one.
        slug: The project.

    Returns:
        The page, or a redirect to the tab Filters after saving; for the script that saves
        a saved filter while it is edited (``save=this``, accepting JSON), its JSON, or 409
        when another filter has the name.

    Raises:
        FilterNameMissing: The name is empty.
        FilterNameTaken: Another filter of the project has the name.
    """
    access, moved = opened(request, slug, "filters/save/")
    if moved:
        return moved
    access.require_write()
    form = request.POST if request.method == "POST" else request.GET
    size = page_size(form)  # of the table it goes back to
    columns = Conjunction.normalized(Column.decode(value) for value in form.getlist("col"))
    saved = saved_filter(access.project, form.get("saved"))
    if request.method == "POST":  # the switches as they are on the page
        on = {int(n) for n in request.POST.getlist("on") if n.isdigit()}
        columns = Conjunction.normalized(operated(switched(columns, on), request.POST))
    changed = saved_columns(form, columns)
    if changed is not None:  # a button of a condition: use the opposite, invert or remove it
        if request.method == "POST":  # a button of the form: what was typed stays
            name = request.POST.get("name", "")
            return save_page(request, access, changed, saved, enabled=False, name=name, size=size)
        address = table_address(changed, page_size(form), saved.pk if saved else None)
        return redirect(access.project.path("filters/save/") + address)
    if request.method == "POST":
        name = " ".join(request.POST.get("name", "").split())[:100]
        if not name:
            raise FilterNameMissing("")
        target = saved if saved and request.POST.get("save") == "this" else None
        other = access.project.filters.filter(name=name).exclude(pk=target.pk if target else None)
        other = other.first()
        autosave = "application/json" in request.headers.get("Accept", "") and target is not None
        if autosave and other is not None:  # saved while editing: no question in between
            return JsonResponse({"saved": False, "taken": name}, status=409)
        if other is not None and request.POST.get("replace") != str(other.pk):
            return save_page(  # another filter has the name: replace it?
                request, access, columns, saved, enabled=False, conflict=other, name=name, size=size
            )
        if other is not None:  # replace it: its conditions and description, its steps stay
            target = other
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
        if autosave:  # saved while editing, by the script of the page
            return JsonResponse({"saved": True, "filter": target.pk, "name": target.name})
        messages.success(request, _("The filter %(name)s is saved.") % {"name": name})
        return redirect(access.project.path("filters/"))
    return save_page(request, access, columns, saved, enabled=saved is None, size=size)


def save_page(
    request: HttpRequest,
    access: ProjectAccess,
    columns: list[Column],
    saved: PullRequestFilter | None,
    enabled: bool,
    conflict: PullRequestFilter | None = None,
    name: str | None = None,
    size: int = PER_PAGE,
):
    """The page of saving a filter, also again with the question whether to replace another one.

    Parameters:
        request: The request.
        access: The project with the rights of the person.
        columns: The columns of conditions.
        saved: The filter that the table showed, if any.
        enabled: Whether every condition is switched on, as for a new filter.
        conflict: Another filter of the name that the person typed: the page asks whether to
            replace it.
        name: The name typed; None for that of the filter.
        size: The size of the table of pull requests, which the page keeps.

    Returns:
        The page.
    """
    repositories = shown_repositories(access)
    labels = Label.objects.filter(repository__in=repositories)
    return render(
        request,
        "pycal_dashboard/project_filter_save.html",
        {
            "project": access.project,
            "access": access,
            "columns": columns,
            "summary": summary(columns, enabled=enabled),
            "saved": saved,
            "conflict": conflict,
            "step": PullRequestStep.objects.filter(filter=saved).first() if saved else None,
            # the conditions, the name or the description differ from the filter as it is saved
            "unsaved": saved is not None
            and (
                [column.encode() for column in columns] != list(saved.columns)
                or (name is not None and name != saved.name)
                or request.POST.get("description", saved.description) != saved.description
            ),
            "original": [  # the filter as it is saved, to restore it before saving a new one
                (value, Column.decode(value).active) for value in saved.columns
            ]
            if saved
            else [],
            "name": saved.name if name is None and saved else (name or ""),
            "description": request.POST.get("description", saved.description if saved else ""),
            "count": len(ColumnResults(repositories, project=access.project).matching(columns)),
            "back": access.project.path("pull-requests/")
            + table_address(columns, size, saved.pk if saved else None),
            "address": table_address(columns, size, saved.pk if saved else None),
            "page_address": access.project.path("filters/save/")
            + table_address(columns, size, saved.pk if saved else None),
            "label_colors": {label.name.lower(): label.color for label in labels},
            "size": size,
            "tab": "filters",
        },
    )
