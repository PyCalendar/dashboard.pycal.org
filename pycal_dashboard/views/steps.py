"""The steps of the pull requests of a project: each a saved filter of what keeps them there.

The tab Steps shows the steps in their order in a bar; a click on a step shows it below, where
the writers and owners name it, write its summary and guide people to remove each condition.
Moving and adding steps work as forms, and with JavaScript without loading the page again.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Max
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.errors import FilterIsAStep, StepNotFound
from pycal_dashboard.models import Issue, Project, PullRequestFilter, PullRequestStep
from pycal_dashboard.services.step_assignment import StepAssignment
from pycal_dashboard.step_template import GROUPS, example, expand

from .projects import opened, pull_requests_of, saved_filter, shown_repositories


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


def conditions_of(step: PullRequestStep) -> list[dict]:
    """The conditions in force of the filter of a step, with how they are explained.

    Parameters:
        step: The step.

    Returns:
        Each condition: its ``index``, ``value``, ``column``, ``summary``, ``description`` and
        the ``preview`` of the description, expanded with values of an example.
    """
    values = example(step.project, step)
    found = []
    for index, value in enumerate(step.filter.columns):
        column = Column.decode(value)
        if column.filter == "all":  # off: no part of the filter
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


def steps_page(request: HttpRequest, slug: str, number: str | None = None):
    """The tab Steps, with one step shown below the bar.

    Parameters:
        request: The request.
        slug: The project.
        number: The step to show; None for the first one.

    Returns:
        The page.
    """
    access, moved = opened(request, slug, "steps/")
    if moved:
        return moved
    steps = list(access.project.steps.select_related("filter"))
    chosen = number or request.GET.get("step")
    shown = step_of(access.project, chosen) if chosen else (steps[0] if steps else None)
    return render(
        request,
        "pycal_dashboard/project_steps.html",
        {
            "project": access.project,
            "access": access,
            "steps": steps,
            "shown": shown,
            "conditions": conditions_of(shown) if shown else [],
            "summary_preview": expand(shown.summary, example(access.project, shown))
            if shown
            else "",
            "free_filters": access.project.filters.filter(step__isnull=True),
            "variables": GROUPS,
            "tab": "steps",
        },
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
        request: The request, with ``name``, ``summary``, ``hidden`` (``on`` to hide it in
            the page of a pull request) and for each condition ``value-<i>``, ``summary-<i>``
            and ``description-<i>``.
        slug: The project.
        number: The step.

    Returns:
        A redirect to the step, or its name for the script that saves while people edit.
    """
    access, _moved = opened(request, slug, "steps/")
    access.require_write()
    step = step_of(access.project, number)
    step.name = " ".join(request.POST.get("name", "").split())[:100] or step.filter.name
    step.summary = request.POST.get("summary", "")
    step.hidden = request.POST.get("hidden") == "on"
    notes = dict(step.conditions or {})
    for value in step.filter.columns:
        index = step.filter.columns.index(value)
        if request.POST.get(f"value-{index}") != value:
            continue
        notes[value] = {
            "summary": " ".join(request.POST.get(f"summary-{index}", "").split())[:200],
            "description": request.POST.get(f"description-{index}", ""),
        }
    step.conditions = notes
    step.save()
    if wants_json(request):  # saved while editing, by the script of the page
        return JsonResponse({"step": step.pk, "name": step.name})
    return redirect(access.project.path("steps/") + f"?step={step.pk}")


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
    pulls = pull_requests_of(repositories).select_related("pull_state")
    if not every:
        pulls = pulls.filter(state=Issue.OPEN)
    steps = list(access.project.steps.all())
    assignment = StepAssignment(access.project, Scope(repositories))
    outside = (
        [
            pull
            for pull in pulls.prefetch_related("labels", "reviews")
            if not assignment.step_of(pull)
        ]
        if steps
        else []
    )
    shown = Paginator(outside, OUTSIDE_PER_PAGE).get_page(request.GET.get("page"))
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
