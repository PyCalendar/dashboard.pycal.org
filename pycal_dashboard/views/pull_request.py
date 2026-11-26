"""The page of one pull request in a project: the steps it goes through and the tasks of each.

The bar at the top shows every step of the project in its order: the complete ones in green
with a check mark, the one the pull request is in chosen, each with a square for each of its
tasks, done in green on the left and to do in red on the right. A click on a step shows its
tasks below: those to do first and open, those done with a check mark and closed.

Writers skip a step or a quality check in a dialog that asks why; the links of the texts
(``{step_skip_url}`` and the others, see
:class:`~pycal_dashboard.services.skip_link.SkipLink`) open the page with that dialog. A
visitor who did not sign in signs in from the dialog, and the reason they typed is kept in the
session until they are back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse, HttpResponseNotModified
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from pycal_dashboard.conditions.group.conjunction import Conjunction
from pycal_dashboard.errors import (
    PullRequestNotFound,
    PullRequestNumberAmbiguous,
    QualityCheckNotFound,
    SkipNotAllowed,
    SkipReasonMissing,
    StepNotFound,
)
from pycal_dashboard.models import CheckSkip, PullRequestComment, PullRequestStep, StepSkip
from pycal_dashboard.services.column_results import ColumnResults
from pycal_dashboard.services.progress import PullRequestProgress
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.pull_request_badge import PullRequestBadge
from pycal_dashboard.services.skip_link import STEP, SkipLink
from pycal_dashboard.services.update_queue import UpdateQueue
from pycal_dashboard.step_template import expand

from .json_page import page, wants_json
from .projects import issue_data, opened, pull_requests_of, shown_repositories

if TYPE_CHECKING:
    from pycal_dashboard.models import Issue, Repository
    from pycal_dashboard.services.progress import StepProgress

BADGE_SECONDS = 300  # how long browsers and GitHub keep a badge before they ask again
# the skip that a person asked for in the session: kept while they sign in, and when they may
# not skip, so that the dialog shows the reason they typed again
SKIP_DRAFT = "skip_draft"
REASON_LENGTH = 2000  # the longest reason to skip


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
    results = ColumnResults(repositories, project=access.project)
    progress = PullRequestProgress(issue, access.project, results.scope, results)
    shown = progress.chosen(request.GET.get("step"))
    if shown and not wants_json(request):  # the JSON has that of every step
        progress.find_evidence([shown])
    keep = {"repository": name} if name else {}
    step_query = "?" + urlencode(keep) + "&step=" if keep else "?step="
    dialog = None
    if shown and request.GET.get("skip") and not wants_json(request):
        dialog = skip_dialog(request, access, issue, shown, request.GET.get("skip", ""))
        if dialog:
            dialog["close_url"] = f"{step_query}{shown.step.pk}"
    return page(
        request,
        "pycal_dashboard/project_pull_request.html",
        {
            **context,
            "pull": issue,
            "progress": progress,
            "shown": shown,
            "step_query": step_query,
            "repository_query": bool(name),
            "step_summary": expand(shown.step.summary, progress.values(shown)) if shown else "",
            "dialog": dialog,
        },
        lambda: {**issue_data(issue), **evidence_data(progress)},
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


@require_http_methods(["GET", "HEAD"])
def project_pull_request_message(request: HttpRequest, slug: str, number: int):
    """The fixed address of the PR message of a pull request (``{pr_message_url}``).

    It leads to the comment of the Status Message of the project on the pull request on GitHub;
    while the pull request does not have it, to the pull request. So the address stays the
    same, also when the comment is written again.

    Parameters:
        request: The request; ``repository`` names the repository of the pull request.
        slug: The project.
        number: The number of the pull request on GitHub.

    Returns:
        A redirect to GitHub.

    Raises:
        PullRequestNotFound: No repository of the project that the person sees has it.
        PullRequestNumberAmbiguous: Several have it, and the address names none.
    """
    access, moved = opened(request, slug, f"pull/{number}/message/")
    if moved:
        return moved
    found = numbered(shown_repositories(access), number, request.GET.get("repository"))
    if len(found) > 1:
        raise PullRequestNumberAmbiguous(str(number))
    issue = found[0]
    comment = PullRequestComment.objects.filter(project=access.project, issue=issue).first()
    if comment is None:
        return redirect(issue.url)
    return redirect(f"{issue.url}#issuecomment-{comment.github_id}")


def evidence_data(progress: PullRequestProgress) -> dict:
    """The progress of a pull request for its JSON, with the evidence of every task.

    Parameters:
        progress: The progress.

    Returns:
        The data, see :meth:`PullRequestProgress.data
        <pycal_dashboard.services.progress.pull_request_progress.PullRequestProgress.data>`.
    """
    progress.find_evidence(progress.steps)
    return progress.data()


def skip_dialog(
    request: HttpRequest,
    access: ProjectAccess,
    issue: Issue,
    shown: StepProgress,
    target: str,
) -> dict | None:
    """The dialog that a link to skip opens on the page of a pull request.

    Parameters:
        request: The request, with the ``key`` of the link of the author, if any.
        access: The rights of the person.
        issue: The pull request.
        shown: The step shown.
        target: ``step``, or the condition of a quality check of the step.

    Returns:
        What the dialog shows: its ``title``, its ``question``, the text of its ``button``, the
        ``target``, the ``key``,
        whether the person ``signed_in`` and is ``allowed`` to skip, and the ``reason`` and the
        ``error`` of a skip that the person asked for before, and the GitHub handle they
        ``signed_in_as`` when they may not skip; None when there is nothing to
        skip, such as a quality check done, or a step skipped already.
    """
    if target == STEP:
        if shown.skip is not None:
            return None
        title = button = _("Skip %(name)s") % {"name": shown.step.name}
        question = _("Why can the step %(name)s be skipped?") % {"name": shown.step.name}
    else:
        task = next((task for task in shown.tasks if task.value == target), None)
        if task is None or not task.skippable:
            return None
        name = task.name
        title = _('Skip the quality check: "%(name)s"') % {"name": name}
        question = _('Why can the quality check "%(name)s" be skipped?') % {"name": name}
        button = _("Skip the quality check")
    key = request.GET.get("key", "")[:40]
    author_link = SkipLink(access.project, issue, shown.step).valid(target, key)
    draft = request.session.get(SKIP_DRAFT) or {}
    mine = draft.get("issue") == issue.pk and draft.get("step") == shown.step.pk
    if mine and draft.get("target") == target:
        request.session.pop(SKIP_DRAFT, None)  # shown in the dialog now
    else:
        draft = {}
    signed_in = request.user.is_authenticated
    allowed = signed_in and access.may_skip(issue, author_link)
    profile = getattr(request.user, "profile", None) if signed_in else None
    return {
        "id": f"skip-{shown.step.pk}-link",
        "step": shown.step.pk,
        "title": title,
        "question": question,
        "button": button,
        "target": target,
        "key": key if author_link else "",
        "signed_in": signed_in,
        "allowed": allowed,
        "reason": draft.get("reason", ""),
        "error": SkipNotAllowed if signed_in and not allowed else None,
        "signed_in_as": profile.github_name if profile and not allowed else "",
    }


def skip_target(step: PullRequestStep, target: str) -> str:
    """The step, or a quality check of its filter, that a form or a link skips.

    Parameters:
        step: The step.
        target: ``step``, or the condition of a quality check, such as
            ``reviews~applies~2``, or its columns joined by AND, such as
            ``status~applies~open&ci~applies~failing``; "" for the step.

    Returns:
        ``step`` or the condition.

    Raises:
        QualityCheckNotFound: The filter of the step has no quality check of this condition.
    """
    if not target or target == STEP:
        return STEP
    checks = {item.encode() for item in Conjunction.of_values(step.filter.columns) if item.checks}
    if target not in checks:
        raise QualityCheckNotFound(target[:60])
    return target


@require_POST
def project_pull_request_skip(request: HttpRequest, slug: str, number: int):
    """Skip a step or a quality check for a pull request with a reason, or remove the skip.

    The pull request is then in the next step that shows it. Its repository is updated in the
    background, so that the message, the labels and the actions of the steps follow. A visitor
    who did not sign in is sent to sign in with GitHub, and the skip is made when they are
    back (:func:`project_pull_request_skip_resume`).

    Parameters:
        request: The request: ``step``, the id of the step, ``skip``, the condition of a
            quality check ("" or ``step`` for the step), ``reason`` or ``remove``, ``key``, the
            key of the link of the author, and ``repository`` when several repositories have
            a pull request of the number.
        slug: The project.
        number: The number of the pull request on GitHub.

    Returns:
        A redirect to the page of the pull request, with the step shown; to signing in.

    Raises:
        ProjectReadOnly: Only the writers and owners remove skips.
        SkipNotAllowed: Only the writers and owners skip, and the author with their link.
        StepNotFound: The project has no such step.
        QualityCheckNotFound: The step has no such quality check.
        SkipReasonMissing: The reason is empty.
    """
    access, _moved = opened(request, slug, f"pull/{number}/")
    name = request.POST.get("repository") or None
    issue = numbered(shown_repositories(access), number, name)[0]
    try:
        step = access.project.steps.select_related("filter").get(
            pk=int(request.POST.get("step") or 0)
        )
    except (ValueError, PullRequestStep.DoesNotExist):
        raise StepNotFound(str(request.POST.get("step", ""))[:20]) from None
    target = skip_target(step, request.POST.get("skip", ""))
    if "remove" in request.POST:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        access.require_write()
        unskip(request, issue, step, target)
        return skipped(access, issue, step, name)
    reason = request.POST.get("reason", "").strip()[:REASON_LENGTH]
    if not reason:
        raise SkipReasonMissing(step.name)
    draft = {
        "issue": issue.pk,
        "step": step.pk,
        "target": target,
        "key": request.POST.get("key", "")[:40],
        "reason": reason,
        "repository": name or "",
    }
    if not request.user.is_authenticated:
        request.session[SKIP_DRAFT] = draft
        return sign_in(access.project.path(f"pull/{number}/skip/resume/"))
    links = SkipLink(access.project, issue, step)
    if not access.may_skip(issue, links.valid(target, draft["key"])):
        request.session[SKIP_DRAFT] = draft  # the dialog shows it again
        access.require_skip(issue, author_link=False)  # raises
    skip(request, issue, step, target, reason)
    return skipped(access, issue, step, name)


@login_required
@require_http_methods(["GET", "HEAD"])
def project_pull_request_skip_resume(request: HttpRequest, slug: str, number: int):
    """Make the skip that a person asked for before signing in, now that they did.

    It was kept in the session (:func:`project_pull_request_skip`), from a form of the site.
    When the person may skip it, it is made as if they clicked **Skip**; else the page shows the
    dialog again, with the reason they typed and the error.

    Parameters:
        request: The request.
        slug: The project.
        number: The number of the pull request on GitHub.

    Returns:
        A redirect to the page of the pull request, with the step shown, or with the dialog.
    """
    access, _moved = opened(request, slug, f"pull/{number}/")
    draft = request.session.pop(SKIP_DRAFT, None) or {}
    issue = next(
        (
            found
            for found in pull_requests_of(shown_repositories(access)).filter(number=number)
            if found.pk == draft.get("issue")
        ),
        None,
    )
    step = access.project.steps.select_related("filter").filter(pk=draft.get("step")).first()
    if issue is None or step is None or not draft.get("reason"):  # nothing asked for
        return redirect(access.project.path(f"pull/{number}/"))
    name = draft.get("repository") or None
    try:
        target = skip_target(step, str(draft.get("target") or ""))
    except QualityCheckNotFound:  # removed in the meantime
        return skipped(access, issue, step, name)
    key = str(draft.get("key") or "")
    if not access.may_skip(issue, SkipLink(access.project, issue, step).valid(target, key)):
        request.session[SKIP_DRAFT] = draft  # the dialog shows the reason and the error
        query = {"step": step.pk, "skip": target} | ({"key": key} if key else {})
        query = ({"repository": name} if name else {}) | query
        return redirect(access.project.path(f"pull/{number}/") + "?" + urlencode(query))
    skip(request, issue, step, target, str(draft["reason"])[:REASON_LENGTH])
    return skipped(access, issue, step, name)


def sign_in(resume: str) -> HttpResponse:
    """Send a visitor to sign in with GitHub, and then to an address.

    Parameters:
        resume: The address to go to after signing in.

    Returns:
        A redirect that keeps the form (307), so that the sign in starts at once, as the
        button of the page of signing in does; to that page when signing in is not set up.
    """
    if not settings.SIGN_IN.configured:
        return redirect_to_login(resume)
    answer = HttpResponse(status=307)
    answer["Location"] = reverse("github_login") + "?" + urlencode({"next": resume})
    return answer


def skip(request: HttpRequest, issue: Issue, step: PullRequestStep, target: str, reason: str):
    """Skip a step or a quality check for a pull request, with the reason.

    Parameters:
        request: The request of the person who skips it.
        issue: The pull request.
        step: The step.
        target: ``step``, or the condition of a quality check.
        reason: Why, in Markdown; its variables are not replaced.
    """
    defaults = {"user": request.user, "reason": reason}
    if target == STEP:
        StepSkip.objects.update_or_create(step=step, issue=issue, defaults=defaults)
        messages.success(request, _("The step %(name)s is skipped.") % {"name": step.name})
    else:
        CheckSkip.objects.update_or_create(
            step=step, issue=issue, condition=target, defaults=defaults
        )
        messages.success(
            request, _("A quality check of the step %(name)s is skipped.") % {"name": step.name}
        )


def unskip(request: HttpRequest, issue: Issue, step: PullRequestStep, target: str):
    """Remove the skip of a step or of a quality check for a pull request.

    Parameters:
        request: The request.
        issue: The pull request.
        step: The step.
        target: ``step``, or the condition of a quality check.
    """
    if target == STEP:
        StepSkip.objects.filter(step=step, issue=issue).delete()
        messages.success(
            request, _("The step %(name)s is not skipped any more.") % {"name": step.name}
        )
    else:
        CheckSkip.objects.filter(step=step, issue=issue, condition=target).delete()
        messages.success(
            request,
            _("The quality check of the step %(name)s is not skipped any more.")
            % {"name": step.name},
        )


def skipped(access: ProjectAccess, issue: Issue, step: PullRequestStep, name: str | None):
    """Update the repository of a pull request after a skip, and show its step.

    Parameters:
        access: The rights of the person.
        issue: The pull request.
        step: The step.
        name: The repository of the address, if it named one.

    Returns:
        A redirect to the page of the pull request with the step shown.
    """
    UpdateQueue.add_repository(issue.repository)  # the message and the labels follow
    query = {"step": step.pk} | ({"repository": name} if name else {})
    return redirect(access.project.path(f"pull/{issue.number}/") + "?" + urlencode(query))
