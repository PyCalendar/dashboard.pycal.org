"""The tab PR Message: the message of a project as a comment on its pull requests.

The page shows the message as one pull request gets it, with its Markdown, the editor of the
template with the variables, and the scope: which pull requests get it. Saving writes it on
all of them in the background, after an update of the project.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse, QueryDict
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_http_methods, require_POST

from pycal_dashboard.markdown_text import render as render_markdown
from pycal_dashboard.models import Issue, Project, PullRequestMessage
from pycal_dashboard.services.message_comments import MessageComments
from pycal_dashboard.services.update_queue import UpdateQueue
from pycal_dashboard.step_template import GROUPS, example, expand

from .projects import opened, shown_repositories

# what a new message starts with
DEFAULT = "{pr_badge}\n\n**{step_name}**\n\n{step_description}\n\n{tasks_all}\n"


def message_of(project: Project, form: QueryDict | None = None) -> PullRequestMessage:
    """The message of a project, with the fields of a form if there is one; not saved.

    Parameters:
        project: The project.
        form: The fields of the page: ``template``, ``listed`` and the switches ``to_listed``,
            ``to_new``, ``to_open`` and ``to_closed``; None for the saved message.

    Returns:
        The message.
    """
    message = PullRequestMessage.objects.filter(project=project).first()
    if message is None:
        message = PullRequestMessage(project=project, template=DEFAULT)
    if form is None:
        return message
    message.template = form.get("template", "")
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


def preview(comments: MessageComments, message: PullRequestMessage) -> dict:
    """The message as a pull request gets it, and how many get it.

    The pull request is the newest in the scope, else the newest open one of the project;
    without pull requests, examples.

    Parameters:
        comments: The comments of the project.
        message: The message.

    Returns:
        ``markdown``, ``pull`` (such as ``collective/icalendar#42``, "" for examples),
        ``count`` and ``button``, the text of the button that saves.
    """
    pulls = comments.pulls(message)
    count = pulls.count()
    pull = (
        pulls.select_related("author", "repository").first()
        or Issue.objects.filter(
            repository__in=comments.repositories, pull_request=True, state=Issue.OPEN
        )
        .select_related("author", "repository")
        .order_by("-created")
        .first()
    )
    if pull is None:
        markdown = expand(message.template, example(comments.project))
    else:
        markdown = expand(message.template, comments.values(pull))
    return {
        "markdown": markdown.strip(),
        "pull": f"{pull.repository.full_name}#{pull.number}" if pull else "",
        "count": count,
        "button": ngettext("Update %(count)s pull request", "Update %(count)s pull requests", count)
        % {"count": count},
    }


@require_http_methods(["GET", "HEAD", "POST"])
def project_message(request: HttpRequest, slug: str):
    """The tab PR Message, public like the project; writers and owners save it.

    Parameters:
        request: The request; POST with the fields of :func:`message_of`.
        slug: The project.

    Returns:
        The page, or a redirect to it after saving.
    """
    access, moved = opened(request, slug, "message/")
    if moved:
        return moved
    if request.method == "POST":
        access.require_write()
        message = message_of(access.project, request.POST)
        wrong = MessageComments.listed(request.POST.get("listed", ""))[1]
        if wrong:
            messages.error(
                request,
                _("These are no numbers of pull requests: %(wrong)s") % {"wrong": ", ".join(wrong)},
            )
        message.updated_by = request.user
        message.save()
        count = MessageComments(access.project).pulls(message).count()
        UpdateQueue.add(access.project, request.user)  # then the comments, in the background
        messages.success(
            request,
            ngettext(
                "The message is saved: %(count)s pull request gets it in the background.",
                "The message is saved: %(count)s pull requests get it in the background.",
                count,
            )
            % {"count": count},
        )
        return redirect(access.project.path("message/"))
    message = message_of(access.project)
    comments = MessageComments(access.project, shown_repositories(access))
    return render(
        request,
        "pycal_dashboard/project_message.html",
        {
            "project": access.project,
            "access": access,
            "message": message,
            "listed": ", ".join(message.listed or []),
            "preview": preview(comments, message),
            "variables": GROUPS,
            "tab": "message",
        },
    )


@login_required
@require_POST
def project_message_preview(request: HttpRequest, slug: str):
    """The live preview of the page while the message is edited, as JSON.

    Parameters:
        request: The request, with the fields of :func:`message_of`.
        slug: The project.

    Returns:
        ``html``, ``markdown``, ``pull``, ``count`` and ``button``; nothing is saved.
    """
    access, _moved = opened(request, slug, "message/")
    access.require_write()
    message = message_of(access.project, request.POST)
    shown = preview(MessageComments(access.project, shown_repositories(access)), message)
    return JsonResponse({**shown, "html": str(render_markdown(shown["markdown"]))})
