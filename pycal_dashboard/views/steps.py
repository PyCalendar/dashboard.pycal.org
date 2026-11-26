"""The steps of the pull requests of a project: each a saved filter of what keeps them there.

The tab Steps shows the steps in their order in a bar; a click on a step shows it below, where
the writers and owners name it, write its summary and guide people to remove each condition.
Moving and adding steps work as forms, and with JavaScript without loading the page again.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Max
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.html import format_html
from django.utils.translation import gettext
from django.views.decorators.http import require_http_methods, require_POST

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.group.conjunction import Conjunction
from pycal_dashboard.errors import FilterIsAStep, StepNotFound
from pycal_dashboard.markdown_text import render as render_markdown
from pycal_dashboard.models import Issue, Label, Project, PullRequestFilter, PullRequestStep
from pycal_dashboard.services.column_results import ColumnResults
from pycal_dashboard.services.step_assignment import StepAssignment
from pycal_dashboard.services.update_queue import UpdateQueue
from pycal_dashboard.step_actions import KINDS, TRIGGERS, labels, normalized
from pycal_dashboard.step_template import STEP_GROUPS, VARIABLE, VARIABLES, example, expand

from .projects import (
    PER_PAGE,
    opened,
    pull_requests_of,
    saved_filter,
    shown_repositories,
    table_address,
)


def wants_json(request: HttpRequest) -> bool:
    """Whether the script of the page sent the request and wants JSON, not a new page.

    Parameters:
        request: The request.

    Returns:
        True for a request of ``fetch`` that accepts JSON.
    """
    return "application/json" in request.headers.get("Accept", "")


def step_of(project: Project, number: int | str | None) -> PullRequestStep:
    """A step of a project by its number.

    Parameters:
        project: The project.
        number: The number of the step.

    Returns:
        The step.

    Raises:
        StepNotFound: The project has no step of this number.
    """
    try:
        return project.steps.select_related("filter").get(pk=int(number or 0))
    except (ValueError, PullRequestStep.DoesNotExist):
        raise StepNotFound(str(number)) from None


# a GitHub handle: letters, digits and single hyphens, at most 39
HANDLE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}")


def labels_follow(project: Project, user: object) -> None:
    """Update the project in the background, so that the step labels follow its steps.

    Parameters:
        project: The project, whose steps changed.
        user: Who changed them.
    """
    if project.step_labels != Project.LABELS_OFF and project.repositories.exists():
        UpdateQueue.add(project, user)


def handles(text: str) -> list[str]:
    """The GitHub handles of a text, separated by commas or spaces, each once.

    Parameters:
        text: Such as ``@niccokunzmann, octocat``.

    Returns:
        The handles that GitHub allows, without ``@``, in their order.

    Examples:
        >>> handles("@niccokunzmann, octocat octocat,  not/valid, ")
        ['niccokunzmann', 'octocat']
    """
    found: list[str] = []
    for part in re.split(r"[,\s]+", text):
        name = part.strip().lstrip("@")
        if HANDLE.fullmatch(name) and name.lower() not in {f.lower() for f in found}:
            found.append(name)
    return found[:100]


def conditions_of(step: PullRequestStep) -> list[dict]:
    """The conditions in force of the filter of a step, with how they are explained.

    Columns joined by AND are one condition, explained once.

    Parameters:
        step: The step.

    Returns:
        Each condition: its ``index``, ``value``, ``column`` (or columns joined by AND),
        ``summary``, ``description`` and the ``preview`` of the description, expanded with
        values of an example.
    """
    values = example(step.project, step)
    found = []
    for index, column in enumerate(Conjunction.of_values(step.filter.columns)):
        value = column.encode()
        if not column.checks:  # off, or a condition of Skip if: no task
            continue
        notes = (step.conditions or {}).get(value, {})
        found.append(
            {
                "index": index,
                "value": value,
                "column": column,
                "summary": notes.get("summary", ""),
                "description": notes.get("description", ""),
                "preview": expand(notes.get("description", ""), values),
                "target": f"description-{index}",
            }
        )
    return found


def back_to(project: Project, address: str) -> str:
    """An address of the project to go back to, such as the review of the message.

    Parameters:
        project: The project.
        address: The address from the request.

    Returns:
        The address if it is a page of the project, else "": no other site.

    Examples:
        >>> from pycal_dashboard.models import Project
        >>> back_to(Project(slug="icalendar"), "https://evil.example/")
        ''
    """
    start = project.path()
    if address.startswith(start) and "//" not in address and "\\" not in address:
        return address
    return ""


# the colors of the background of steps, light enough for dark text; "" for none
STEP_COLORS = (
    "",
    "#fecaca",
    "#fed7aa",
    "#fde68a",
    "#bbf7d0",
    "#a5f3fc",
    "#bfdbfe",
    "#ddd6fe",
    "#fbcfe8",
)


def steps_page(request: HttpRequest, slug: str, number: str | None = None):
    """The tab Steps, with one step shown below the bar.

    Parameters:
        request: The request: ``step_id`` (or ``step``) is the id of the step to show, as the
            labels of the steps on GitHub link it.
        slug: The project.
        number: The step to show; None for the first one.

    Returns:
        The page; with the status 404 and a notice for the id of a step that the project does
        not have (any more), such as one that was removed.
    """
    access, moved = opened(request, slug, "steps/")
    if moved:
        return moved
    steps = list(access.project.steps.select_related("filter"))
    if not access.can_write:  # who only reads the project sees the steps that are visible
        steps = [step for step in steps if not step.hidden]
    chosen = number or request.GET.get("step_id") or request.GET.get("step")
    missing = ""
    try:
        shown = step_of(access.project, chosen) if chosen else (steps[0] if steps else None)
    except StepNotFound:  # such as a link of a label to a step that was removed
        missing, shown = str(chosen)[:20], None
    if shown is None or shown not in steps:  # missing or hidden from the person: the first one
        shown = steps[0] if steps else None
    return render(
        request,
        "pycal_dashboard/project_steps.html",
        {
            "project": access.project,
            "access": access,
            "steps": steps,
            "shown": shown,
            "conditions": conditions_of(shown) if shown else [],
            "skip_conditions": [
                column for column in Conjunction.of_values(shown.filter.columns) if column.skips
            ]
            if shown
            else [],
            "summary_preview": expand(shown.summary, example(access.project, shown))
            if shown
            else "",
            "free_filters": access.project.filters.filter(step__isnull=True),
            "back": back_to(access.project, request.GET.get("back", "")),
            "colors": STEP_COLORS,
            "filter_edit": access.project.path("filters/save/")
            + table_address(
                [Column.decode(value) for value in shown.filter.columns],
                PER_PAGE,
                shown.filter.pk,
            )
            if shown
            else "",
            "filter_pulls": access.project.path("pull-requests/")
            + table_address(
                [Column.decode(value) for value in shown.filter.columns],
                PER_PAGE,
                shown.filter.pk,
            )
            if shown
            else "",
            "actions": normalized(shown.actions if shown else None),
            "label_names": sorted(
                set(
                    Label.objects.filter(
                        repository__in=access.project.repositories.all()
                    ).values_list("name", flat=True)
                )
            ),
            "variables": STEP_GROUPS,
            "missing": missing,
            "tab": "steps",
        },
        status=404 if missing else 200,
    )


@require_http_methods(["GET", "HEAD"])
def project_steps(request: HttpRequest, slug: str):
    """The steps of the pull requests of a project, public like the project.

    Parameters:
        request: The request; ``step`` is the number of the step to show.
        slug: The project.

    Returns:
        The page.
    """
    return steps_page(request, slug)


@login_required
@require_POST
def project_step_add(request: HttpRequest, slug: str):
    """Make a saved filter a step, the last one.

    Parameters:
        request: The request, with ``filter``, the number of the filter.
        slug: The project.

    Returns:
        A redirect to the new step, or its JSON for the script of the page.

    Raises:
        FilterIsAStep: The filter is a step already.
    """
    access, _moved = opened(request, slug, "steps/")
    access.require_write()
    saved: PullRequestFilter = saved_filter(access.project, request.POST.get("filter"))
    if saved is None or PullRequestStep.objects.filter(filter=saved).exists():
        raise FilterIsAStep(str(request.POST.get("filter", "")))
    last = access.project.steps.aggregate(last=Max("position"))["last"]
    step = PullRequestStep.objects.create(
        project=access.project,
        filter=saved,
        name=saved.name,
        position=0 if last is None else last + 1,
    )
    labels_follow(access.project, request.user)
    url = access.project.path("steps/") + f"?step={step.pk}"
    if wants_json(request):
        return JsonResponse({"step": step.pk, "name": step.name, "url": url}, status=201)
    return redirect(url)


@login_required
@require_POST
def project_step_move(request: HttpRequest, slug: str, number: int):
    """Move a step to another place in the bar: ``to`` a position, or ``up`` and ``down``.

    Parameters:
        request: The request, with ``to`` (the new position from 0) or ``direction``
            (``left`` or ``right``).
        slug: The project.
        number: The step.

    Returns:
        A redirect to the step, or nothing for the script of the page.
    """
    access, _moved = opened(request, slug, "steps/")
    access.require_write()
    step = step_of(access.project, number)
    steps = list(access.project.steps.all())
    index = steps.index(step)
    if "to" in request.POST:
        try:
            to = int(request.POST["to"])
        except ValueError:
            to = index
    else:
        to = index + (-1 if request.POST.get("direction") == "left" else 1)
    to = min(max(to, 0), len(steps) - 1)
    steps.insert(to, steps.pop(index))
    with transaction.atomic():
        for position, moved in enumerate(steps):
            if moved.position != position:
                PullRequestStep.objects.filter(pk=moved.pk).update(position=position)
    if wants_json(request):
        return HttpResponse(status=204)
    return redirect(access.project.path("steps/") + f"?step={step.pk}")


@login_required
@require_POST
def project_step_edit(request: HttpRequest, slug: str, number: int):
    """Save the name and summary of a step, and the summary and description of its conditions.

    Parameters:
        request: The request, with ``name``, ``summary``, ``visible`` (``on`` to show it in
            the page of a pull request, with ``visible_form``), ``color`` (one of
            :data:`STEP_COLORS`), ``enter_add``, ``enter_remove``, ``complete_add`` and
            ``complete_remove`` (the labels separated by commas that the GitHub App adds or
            removes when a pull request enters or leaves the step, with ``actions_form``)
            and for each condition
            ``value-<i>``, ``summary-<i>`` and ``description-<i>``.
        slug: The project.
        number: The step.

    Returns:
        A redirect to the step, or its name for the script that saves while people edit.
    """
    access, _moved = opened(request, slug, "steps/")
    access.require_write()
    step = step_of(access.project, number)
    before = (step.name, step.color)
    step.name = " ".join(request.POST.get("name", "").split())[:100] or step.filter.name
    step.summary = request.POST.get("summary", "")
    if request.POST.get("visible_form"):  # the switch: unchecked is not sent
        step.hidden = request.POST.get("visible") != "on"
    color = request.POST.get("color", step.color)
    # one of the palette, or the color it has, which may come from its label on GitHub
    step.color = color if color in STEP_COLORS or color == step.color else ""
    if request.POST.get("skip_form"):  # the field: empty is nobody
        step.skip_authors = handles(request.POST.get("skip_authors", ""))
    if request.POST.get("actions_form"):  # the form shows the actions: empty fields have none
        step.actions = {
            trigger: {kind: labels(request.POST.get(f"{trigger}_{kind}", "")) for kind in KINDS}
            for trigger in TRIGGERS
        }
    notes = dict(step.conditions or {})
    for index, condition in enumerate(Conjunction.of_values(step.filter.columns)):
        value = condition.encode()  # of a column, or of columns joined by AND
        if request.POST.get(f"value-{index}") != value:
            continue
        notes[value] = {
            "summary": " ".join(request.POST.get(f"summary-{index}", "").split())[:200],
            "description": request.POST.get(f"description-{index}", ""),
        }
    step.conditions = notes
    step.save()
    if (step.name, step.color) != before:
        labels_follow(access.project, request.user)
    if wants_json(request):  # saved while editing, by the script of the page
        return JsonResponse({"step": step.pk, "name": step.name, "color": step.color})
    address = access.project.path("steps/") + f"?step={step.pk}"
    back = back_to(access.project, request.POST.get("back", ""))
    return redirect(address + (f"&{urlencode({'back': back})}" if back else ""))


@login_required
@require_POST
def project_step_remove(request: HttpRequest, slug: str, number: int):
    """Remove a step; its filter stays.

    Parameters:
        request: The request.
        slug: The project.
        number: The step.

    Returns:
        A redirect to the tab Steps.
    """
    access, _moved = opened(request, slug, "steps/")
    access.require_write()
    step_of(access.project, number).delete()
    return redirect(access.project.path("steps/"))


OUTSIDE_PER_PAGE = 50


@require_http_methods(["GET", "HEAD"])
def project_steps_check(request: HttpRequest, slug: str):
    """The pull requests outside of the usual steps: no task of any step applies to them.

    Open pull requests by default; ``all`` also lists the closed and merged ones, which are
    mostly outside, as they are done.

    Parameters:
        request: The request; ``all`` for every pull request, ``page`` the page.
        slug: The project.

    Returns:
        The page.
    """
    access, moved = opened(request, slug, "steps/check/")
    if moved:
        return moved
    repositories = shown_repositories(access)
    every = request.GET.get("all") == "1"
    steps = list(access.project.steps.all())
    results = ColumnResults(repositories, project=access.project)
    places = StepAssignment(access.project, results.scope).step_of_all(results) if steps else {}
    open_ids = (
        None
        if every
        else set(
            pull_requests_of(repositories).filter(state=Issue.OPEN).values_list("pk", flat=True)
        )
    )
    outside = [pk for pk, step in places.items() if step is None and (every or pk in open_ids)]
    shown = Paginator(outside, OUTSIDE_PER_PAGE).get_page(request.GET.get("page"))
    loaded = pull_requests_of(repositories).in_bulk(list(shown.object_list))
    shown.object_list = [loaded[pk] for pk in shown.object_list if pk in loaded]
    return render(
        request,
        "pycal_dashboard/project_steps_check.html",
        {
            "project": access.project,
            "access": access,
            "steps": steps,
            "pulls": shown,
            "every": every,
            "repositories": repositories,
            "tab": "steps",
        },
    )


@login_required
@require_POST
def project_step_preview(request: HttpRequest, slug: str, number: int):
    """The preview of a template of a step: the Markdown with an example pull request.

    A note above it says so when the text uses variables; without them, it is the Markdown as
    it is.

    Parameters:
        request: The request, with ``text``.
        slug: The project.
        number: The step.

    Returns:
        The cleaned HTML.
    """
    access, _moved = opened(request, slug, "steps/")
    step = step_of(access.project, number)
    text = request.POST.get("text", "")
    html = render_markdown(expand(text, example(access.project, step)))
    if VARIABLE.search(text) and any(name in VARIABLES for name in VARIABLE.findall(text)):
        note = gettext("With an example pull request:")
        html = format_html('<p class="muted template-note">{}</p>{}', note, html)
    return HttpResponse(html)
