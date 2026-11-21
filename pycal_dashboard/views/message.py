"""The tab PR Message: the message of a project as a comment on its pull requests.

Editing it is a flow of four pages: the current message (or none), the editor of its
template, the review of the draft with example pull requests in every state of the steps,
and the scope: which pull requests get it. The draft stays in the session of the person until
the scope saves it; then the comments are written in the background, after an update.
"""

from __future__ import annotations

from collections.abc import Callable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse, QueryDict
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_http_methods, require_POST

from pycal_dashboard.markdown_text import render as render_markdown
from pycal_dashboard.models import Issue, Project, PullRequestMessage
from pycal_dashboard.services.example_pulls import ExamplePulls
from pycal_dashboard.services.message_comments import MessageComments
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.update_queue import UpdateQueue
from pycal_dashboard.step_template import GROUPS, example, expand

from .projects import opened, shown_repositories

# what a new message starts with
DEFAULT = "{pr_badge}\n\n**{step_name}**\n\n{step_description}\n\n{tasks_all}\n"
# the pages of editing, in their order: their names and addresses after the project
FLOW = (
    ("message", "message/"),
    ("edit", "message/edit/"),
    ("review", "message/review/"),
    ("scope", "message/scope/"),
)


def draft_key(project: Project) -> str:
    """The key of the draft of the template of a project in the session.

    Parameters:
        project: The project.

    Returns:
        The key.
    """
    return f"message-draft:{project.pk}"


def saved_message(project: Project) -> PullRequestMessage | None:
    """The saved message of a project.

    Parameters:
        project: The project.

    Returns:
        The message; None without one.
    """
    return PullRequestMessage.objects.filter(project=project).first()


def draft_of(request: HttpRequest, project: Project) -> str:
    """The template being edited: the draft of the session, else the saved one, else the default.

    Parameters:
        request: The request, with the session.
        project: The project.

    Returns:
        The template.
    """
    draft = request.session.get(draft_key(project))
    if draft is not None:
        return draft
    message = saved_message(project)
    return message.template if message else DEFAULT


def with_scope(message: PullRequestMessage, form: QueryDict) -> PullRequestMessage:
    """The message with the scope of a form: ``listed`` and the switches; not saved.

    Parameters:
        message: The message.
        form: ``listed``, ``to_listed``, ``to_new``, ``to_open`` and ``to_closed``.

    Returns:
        The message.
    """
    message.listed = MessageComments.listed(form.get("listed", ""))[0]
    message.to_listed = form.get("to_listed") == "on"
    message.to_open = form.get("to_open") == "on"
    message.to_closed = form.get("to_closed") == "on"
    to_new = form.get("to_new") == "on"
    if to_new and not (message.to_new and message.new_since):
        message.new_since = timezone.now()  # new from now on
    if not to_new:
        message.new_since = None
    message.to_new = to_new
    return message


def chosen_pull(comments: MessageComments, text: str) -> Issue | None:
    """The pull request that the person asked to see the message of.

    Parameters:
        comments: The comments of the project.
        text: Such as ``2166`` or ``collective/icalendar#2166``.

    Returns:
        The pull request; None if the project has none of the number.
    """
    names = MessageComments.listed(text)[0]
    if not names:
        return None
    repository, _hash, number = names[0].rpartition("#")
    pulls = Issue.objects.filter(
        repository__in=comments.repositories, pull_request=True, number=int(number)
    )
    if repository:
        pulls = pulls.filter(repository__full_name__iexact=repository)
    return pulls.select_related("author", "repository").order_by("-created").first()


def preview(
    comments: MessageComments,
    message: PullRequestMessage,
    index: int | str | None = None,
    pull_text: str = "",
) -> dict:
    """The message as a pull request gets it, and how many get it.

    The pull request is the one asked for by its number; else the example of ``index``: one
    for each number of tasks done, from none to all (:class:`ExamplePulls`); else the newest
    in the scope, else the newest open one; without pull requests, examples of the values.

    Parameters:
        comments: The comments of the project.
        message: The message.
        index: The example, from 0; None for the first one.
        pull_text: A pull request to see, such as ``2166``; "" for the examples.

    Returns:
        ``markdown``, ``pull`` (such as ``collective/icalendar#42``, "" for examples),
        ``count`` and ``button`` (the text of the button that saves), ``example`` and
        ``examples`` (its place and how many there are), ``label`` (what the example is)
        ``missing`` (the pull request asked for that the project lacks, else ""), and the
        ``step_id`` and ``step_name`` of the step the pull request is in, "" for none.
    """
    pulls = comments.pulls(message)
    count = pulls.count()
    examples = ExamplePulls(comments.project, comments.results).examples()
    try:
        place = min(max(int(index or 0), 0), len(examples) - 1) if examples else 0
    except ValueError:
        place = 0
    label, missing = "", ""
    pull = chosen_pull(comments, pull_text) if pull_text.strip() else None
    if pull_text.strip() and pull is None:
        missing = _("The project has no pull request %(pull)s.") % {"pull": pull_text.strip()}
    if pull is None and examples:
        shown = examples[place]
        pull = Issue.objects.select_related("author", "repository").get(pk=shown["pk"])
        where = shown["step"] or _("outside of the steps")
        label = _("Example %(number)s of %(count)s: %(step)s, %(done)s of %(total)s tasks done") % {
            "number": place + 1,
            "count": len(examples),
            "step": where,
            "done": shown["done"],
            "total": shown["total"],
        }
    if pull is None:
        pull = (
            pulls.select_related("author", "repository").first()
            or Issue.objects.filter(
                repository__in=comments.repositories, pull_request=True, state=Issue.OPEN
            )
            .select_related("author", "repository")
            .order_by("-created")
            .first()
        )
    values = comments.values(pull) if pull else example(comments.project)
    markdown = expand(message.template, values)
    return {
        "markdown": markdown.strip(),
        "pull": f"{pull.repository.full_name}#{pull.number}" if pull else "",
        "count": count,
        "button": ngettext("Update %(count)s pull request", "Update %(count)s pull requests", count)
        % {"count": count},
        "example": place,
        "examples": len(examples),
        "label": label,
        "missing": missing,
        "step_id": values.get("step_id", "") if pull else "",
        "step_name": values.get("step_name", "") if pull else "",
    }


def flow_page(
    request: HttpRequest,
    slug: str,
    page: str,
    template: str,
    context: Callable[[ProjectAccess, MessageComments], dict],
):
    """A page of the flow of editing the message.

    Parameters:
        request: The request.
        slug: The project.
        page: Its name in :data:`FLOW`.
        template: The template of the page.
        context: A function of the rights of the person and the comments of the project that
            gives more of the context.

    Returns:
        The page, or a redirect to the address of the project now.
    """
    access, moved = opened(request, slug, dict(FLOW)[page])
    if moved:
        return moved
    if page != "message":
        access.require_write()
    comments = MessageComments(access.project, shown_repositories(access))
    return render(
        request,
        template,
        {
            "project": access.project,
            "access": access,
            "flow": [name for name, _address in FLOW],
            "page": page,
            "comments": comments,
            "editing": draft_key(access.project) in request.session,
            "tab": "message",
        }
        | context(access, comments),
    )


@require_http_methods(["GET", "HEAD"])
def project_message(request: HttpRequest, slug: str):
    """1. The message as a pull request gets it, and its scope; or that there is none.

    Public like the project, also the examples in every state of the steps; writers and owners
    start editing it.

    Parameters:
        request: The request; ``example`` the example from 0, ``pull`` a pull request to see
            instead, ``view=markdown`` the Markdown.
        slug: The project.

    Returns:
        The page.
    """

    def context(access: ProjectAccess, comments: MessageComments) -> dict:
        message = saved_message(access.project)
        return {
            "message": message,
            "preview": preview(
                comments, message, request.GET.get("example"), request.GET.get("pull", "")
            )
            if message
            else None,
            "pull_text": request.GET.get("pull", ""),
            "markdown_view": request.GET.get("view") == "markdown",
        }

    return flow_page(request, slug, "message", "pycal_dashboard/message/show.html", context)


@require_http_methods(["GET", "HEAD", "POST"])
def project_message_edit(request: HttpRequest, slug: str):
    """2. The editor of the template; the next page keeps it as a draft of the session.

    Parameters:
        request: The request; POST with ``template``.
        slug: The project.

    Returns:
        The page, or a redirect to the review.
    """
    if request.method == "POST":
        access, _moved = opened(request, slug, "message/edit/")
        access.require_write()
        request.session[draft_key(access.project)] = request.POST.get("template", "")
        return redirect(access.project.path("message/review/"))

    def context(access: ProjectAccess, comments: MessageComments) -> dict:
        return {"template": draft_of(request, access.project), "variables": GROUPS}

    return flow_page(request, slug, "edit", "pycal_dashboard/message/edit.html", context)


@login_required
@require_http_methods(["GET", "HEAD"])
def project_message_review(request: HttpRequest, slug: str):
    """3. The draft as example pull requests get it, from no task done to all of them.

    Parameters:
        request: The request; ``example`` the example from 0, ``pull`` a pull request to see
            instead, ``view=markdown`` the Markdown.
        slug: The project.

    Returns:
        The page.
    """

    def context(access: ProjectAccess, comments: MessageComments) -> dict:
        message = saved_message(access.project) or PullRequestMessage(project=access.project)
        message.template = draft_of(request, access.project)
        shown = preview(comments, message, request.GET.get("example"), request.GET.get("pull", ""))
        back = access.project.path("message/review/") + "?" + request.GET.urlencode()
        return {
            "preview": shown,
            "pull_text": request.GET.get("pull", ""),
            "markdown_view": request.GET.get("view") == "markdown",
            "back": back,
        }

    return flow_page(request, slug, "review", "pycal_dashboard/message/review.html", context)


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def project_message_scope(request: HttpRequest, slug: str):
    """4. The scope: which pull requests get the message; saving updates them in the background.

    Parameters:
        request: The request; POST with the fields of :func:`with_scope` and ``save``, or
            ``cancel``.
        slug: The project.

    Returns:
        The page, or a redirect to the message.
    """
    if request.method == "POST":
        access, _moved = opened(request, slug, "message/scope/")
        access.require_write()
        project = access.project
        if "cancel" in request.POST:
            request.session.pop(draft_key(project), None)
            return redirect(project.path("message/"))
        message = saved_message(project) or PullRequestMessage(project=project)
        message.template = draft_of(request, project)
        with_scope(message, request.POST)
        wrong = MessageComments.listed(request.POST.get("listed", ""))[1]
        if wrong:
            messages.error(
                request,
                _("These are no numbers of pull requests: %(wrong)s") % {"wrong": ", ".join(wrong)},
            )
        message.updated_by = request.user
        message.save()
        request.session.pop(draft_key(project), None)
        count = MessageComments(project).pulls(message).count()
        UpdateQueue.add(project, request.user)  # then the comments, in the background
        messages.success(
            request,
            ngettext(
                "The message is saved: %(count)s pull request gets it in the background.",
                "The message is saved: %(count)s pull requests get it in the background.",
                count,
            )
            % {"count": count},
        )
        return redirect(project.path("message/"))

    def context(access: ProjectAccess, comments: MessageComments) -> dict:
        message = saved_message(access.project) or PullRequestMessage(project=access.project)
        if "count" in request.GET:  # the button Count, without JavaScript
            with_scope(message, request.GET)
        count = comments.pulls(message).count()
        return {
            "message": message,
            "listed": ", ".join(message.listed or []),
            "button": ngettext(
                "Update %(count)s pull request", "Update %(count)s pull requests", count
            )
            % {"count": count},
        }

    return flow_page(request, slug, "scope", "pycal_dashboard/message/scope.html", context)


@login_required
@require_POST
def project_message_preview(request: HttpRequest, slug: str):
    """The preview of the editor of the template (HTML), or the count of a scope (JSON).

    Parameters:
        request: The request: ``text``, the template, for its HTML with the first example; or
            the fields of :func:`with_scope` for how many pull requests get it.
        slug: The project.

    Returns:
        The HTML, or ``count`` and ``button`` as JSON; nothing is saved.
    """
    access, _moved = opened(request, slug, "message/")
    access.require_write()
    comments = MessageComments(access.project, shown_repositories(access))
    message = saved_message(access.project) or PullRequestMessage(project=access.project)
    if "text" in request.POST:
        message.template = request.POST["text"]
        return HttpResponse(render_markdown(preview(comments, message)["markdown"]))
    with_scope(message, request.POST)
    count = comments.pulls(message).count()
    button = ngettext("Update %(count)s pull request", "Update %(count)s pull requests", count)
    return JsonResponse({"count": count, "button": button % {"count": count}})
