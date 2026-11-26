"""The projects: the public list, the overview of a project, and the pages that change it."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_http_methods, require_POST

from pycal_dashboard.conditions.group.column import FILTERS, GROUPS, Column
from pycal_dashboard.conditions.group.conjunction import Conjunction
from pycal_dashboard.conditions.review_kinds import ALL as REVIEW_KINDS
from pycal_dashboard.errors import (
    BackupInvalid,
    ConditionInputUnknown,
    DashboardError,
    FilterNotFound,
    GitHubTokenMissing,
    ProjectNotFound,
    all_errors,
    translate,
)
from pycal_dashboard.github.permissions import EVENTS, REQUIRED
from pycal_dashboard.github.person_client import PersonClient
from pycal_dashboard.import_guard import IMPORT_GUARD
from pycal_dashboard.models import (
    Issue,
    Label,
    Project,
    ProjectMember,
    PullRequestFilter,
    Repository,
)
from pycal_dashboard.services.column_results import ColumnResults
from pycal_dashboard.services.handle_completion import HandleCompletion
from pycal_dashboard.services.identity import GitHubIdentity
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.project_status import ProjectStatus
from pycal_dashboard.services.repository_lookup import RepositoryLookup
from pycal_dashboard.services.snapshot_editor import SnapshotEditor
from pycal_dashboard.services.update_queue import UpdateQueue
from pycal_dashboard.services.update_worker import UpdateWorker

from .json_page import page

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser

    from pycal_dashboard.models import Installation, Project


# the pages that a change of the address goes back to
BACK_PAGES = {"settings/", "settings/repositories/"}
# the repositories offered while typing, of those the site knows
KNOWN_CHOICES = 200
MAX_BACKUP = 1_000_000  # bytes of a file of a backup, see ProjectBackup
MIN_SEARCH = 2


def shown_repositories(access: ProjectAccess) -> list[Repository]:
    """The repositories of a project that a person sees.

    A public project may contain a repository that became private after it was added: only the
    collaborators of the project see it.

    Parameters:
        access: The project with the rights of the person.

    Returns:
        The repositories.
    """
    repositories = access.project.repositories.select_related("installation")
    if not access.is_member:
        repositories = repositories.filter(private=False)
    return list(repositories)


def project_data(access: ProjectAccess, repositories: list[Repository]) -> dict:
    """The public information of a project, for its JSON.

    Parameters:
        access: The project with the rights of the visitor.
        repositories: The repositories the visitor sees.

    Returns:
        The data.
    """
    project = access.project
    return {
        "name": project.name,
        "slug": project.slug,
        "description": project.description,
        "url": access_url(project),
        "updated": project.updated.isoformat() if project.updated else None,
        "open_issues": total(repositories, "open_issues"),
        "open_pull_requests": total(repositories, "open_pull_requests"),
        "repositories": [
            {
                "full_name": r.full_name,
                "url": r.url,
                "open_issues": r.open_issues,
                "open_pull_requests": r.open_pull_requests,
                "updated": r.updated.isoformat() if r.updated else None,
                "app": app_data(r.installation),
            }
            for r in repositories
        ],
        "app_requires": {"permissions": dict(REQUIRED), "events": list(EVENTS)},
    }


def app_data(installation: Installation | None) -> dict | None:
    """The installation of the GitHub App on a repository, for the JSON of its project.

    What it was granted and receives, as GitHub last told, and what of ``app_requires``
    it lacks, so that a missing permission can be found.

    Parameters:
        installation: The installation; None when the app is not installed on the repository.

    Returns:
        ``installed`` (active: neither removed nor suspended), ``account``, ``permissions``,
        ``events``, ``missing_permissions`` and ``missing_events``; None without one.
    """
    if installation is None:
        return None
    events = list(installation.events or [])
    return {
        "installed": not installation.removed and not installation.suspended,
        "account": installation.account_login,
        "permissions": dict(sorted((installation.permissions or {}).items())),
        "events": sorted(events),
        "missing_permissions": installation.missing_permissions,
        "missing_events": [event for event in EVENTS if event not in events],
    }


def access_url(project: Project) -> str:
    """The path of the page of a project.

    Parameters:
        project: The project.

    Returns:
        The path.
    """
    return project.path()


def opened(request: HttpRequest, slug: str, page: str = ""):
    """The project of an address, and where to go if it has another address now.

    Parameters:
        request: The request.
        slug: The slug in the address: the current one, an old one or one in other case.
        page: The page of the project, such as ``repositories/``.

    Returns:
        The rights of the person in the project, and a permanent redirect to its address for a
        GET with another slug, else None.

    Raises:
        ProjectNotFound: The person sees no project with this slug.
    """
    access = ProjectAccess.of(slug, request.user)
    if access.project.slug == slug or request.method not in ("GET", "HEAD"):
        return access, None
    query = request.META.get("QUERY_STRING", "")
    target = access.project.path(page) + (f"?{query}" if query else "")
    return access, HttpResponsePermanentRedirect(target)


def total(repositories: list[Repository], field: str) -> int | None:
    """The sum of a number of the repositories that were read.

    Parameters:
        repositories: The repositories.
        field: ``open_issues`` or ``open_pull_requests``.

    Returns:
        The sum, None if none was read.

    Examples:
        >>> total([Repository(open_issues=2), Repository(open_issues=None)], "open_issues")
        2
        >>> total([], "open_issues") is None
        True
    """
    numbers = [getattr(r, field) for r in repositories if getattr(r, field) is not None]
    return sum(numbers) if numbers else None


def projects(request: HttpRequest):
    """The projects that the visitor sees: all public ones, and private ones of their own.

    Parameters:
        request: The request; ``mine`` lists only the projects of the person, of which they
            are a collaborator (the menu of the account links it).

    Returns:
        The page or ``/projects.json``.
    """
    mine = request.GET.get("mine") == "1" and request.user.is_authenticated
    visible = ProjectAccess.visible(request.user)
    if mine:
        visible = visible.filter(members__user=request.user).distinct()
    found = list(visible.prefetch_related("repositories"))
    return page(
        request,
        "pycal_dashboard/projects.html",
        {"projects": found, "mine": mine},
        lambda: {
            "projects": [
                {
                    "name": project.name,
                    "slug": project.slug,
                    "description": project.description,
                    "url": access_url(project),
                    "repositories": [
                        r.full_name for r in project.repositories.all() if not r.private
                    ],
                }
                for project in found
            ]
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def project_new(request: HttpRequest):
    """Create a project: its name, description and whether it is public.

    Parameters:
        request: The request.

    Returns:
        The form, or the page that adds repositories to the new project.
    """
    form = {"name": "", "description": "", "public": True, "slug": ""}
    if request.method == "POST":
        form = {
            "name": request.POST.get("name", ""),
            "description": request.POST.get("description", ""),
            "public": request.POST.get("visibility", "public") == "public",
            "slug": request.POST.get("slug", ""),
        }
        project = ProjectEditor.create(request.user, **form)
        messages.success(
            request, _("The project %(name)s is created. Add its repositories.") % {"name": project}
        )
        return redirect(project.path("settings/repositories/"))
    return render(request, "pycal_dashboard/project_form.html", {"form": form, "new": True})


PAGES = {"": "", "update": "", "settings": "settings/", "address": "settings/"}
PAGES |= {
    "repositories": "settings/repositories/",
    "collaborators": "settings/collaborators/",
}
PAGES["pull-requests"] = "pull-requests/"
PAGES["filters"] = "filters/"
PAGES["steps"] = "steps/"
PAGES["people"] = "settings/collaborators/"  # the tab before it was called Collaborators


def project_moved(request: HttpRequest, slug: str, name: str = "", page: str = ""):
    """An address of a project from before: with its name after the slug, or the tab People.

    Parameters:
        request: The request.
        slug: The project in the address.
        name: The name of the project, or ``people``.
        page: The page after the name, "" for the overview.

    Returns:
        A permanent redirect to the page at the address of the project now.

    Raises:
        ProjectNotFound: The person sees no such project, or the page does not exist.
    """
    access = ProjectAccess.of(slug, request.user)
    if page not in PAGES:
        raise ProjectNotFound(slug)
    query = request.META.get("QUERY_STRING", "")
    target = access.project.path(PAGES[page]) + (f"?{query}" if query else "")
    return HttpResponsePermanentRedirect(target)


def update_errors(project: Project, repositories: list[Repository]) -> dict:
    """The repositories whose last update failed, for the notice at the top of the overview.

    Parameters:
        project: The project.
        repositories: The repositories that the person sees: a private one only for its
            collaborators, so the notice shows nothing that they may not see.

    Returns:
        ``update_errors``: each repository with its class of error, and ``dismiss_key``, which
        changes with every new failure, so that a notice clicked away comes back for a new one.
    """
    failed = [r for r in repositories if r.error_code]
    errors = all_errors()
    times = [r.error_at.isoformat() for r in failed if r.error_at]
    return {
        "update_errors": [{"repository": r, "error": errors.get(r.error_code)} for r in failed],
        "dismiss_key": f"update-errors:{project.slug}:{max(times) if times else ''}",
    }


def project(request: HttpRequest, slug: str):
    """The overview of a project: its repositories with their open issues and pull requests.

    Parameters:
        request: The request.
        slug: The project in the address.

    Returns:
        The page or its JSON.
    """
    access, moved = opened(request, slug)
    if moved:
        return moved
    repositories = shown_repositories(access)
    status = ProjectStatus.of(access.project, repositories)
    if status.state in ("outdated", "never") and UpdateQueue.stale(access.project):
        status = ProjectStatus.of(access.project, repositories)  # what may be out of date
    if status.updating:
        UpdateWorker.start()  # takes up a job that a stopped process left behind
    return page(
        request,
        "pycal_dashboard/project.html",
        {
            "project": access.project,
            "access": access,
            "repositories": repositories,
            "status": status,
            "open_issues": total(repositories, "open_issues"),
            "open_pull_requests": total(repositories, "open_pull_requests"),
            "tab": "overview",
            **update_errors(access.project, repositories),
        },
        lambda: project_data(access, repositories),
    )


# the pull requests of a page, which the visitor chooses: at most 100, also in the JSON
PER_PAGE_CHOICES = (10, 25, 50, 100)
PER_PAGE = 25
# the columns of the table of pull requests that the visitor shows or hides, and whether each
# is shown before the visitor chooses
PULL_REQUEST_COLUMNS = (
    ("status", gettext_lazy("Status"), False),
    ("title", gettext_lazy("Title"), True),
    ("step", gettext_lazy("Step"), True),  # the badge, linked to the page of the pull request
    ("organization", gettext_lazy("Organization"), False),
    ("repository", gettext_lazy("Repository"), False),
    ("number", gettext_lazy("Number"), True),
    ("creator", gettext_lazy("Creator"), True),
    ("created", gettext_lazy("Created"), False),
)


def pull_requests_of(repositories: list[Repository]) -> QuerySet[Issue]:
    """The pull requests of repositories together, the newest first.

    Parameters:
        repositories: The repositories that the person sees.

    Returns:
        The query of the pull requests.
    """
    return (
        Issue.objects.filter(repository__in=repositories, pull_request=True)
        .select_related("author", "repository")
        .order_by("-created", "-pk")
    )


def per_page(request: HttpRequest) -> int:
    """How many pull requests a page shows: ``per_page`` of the request, at most 100.

    Parameters:
        request: The request.

    Returns:
        A number of :data:`PER_PAGE_CHOICES`; the default for another one.
    """
    try:
        wanted = int(request.GET.get("per_page", PER_PAGE))
    except ValueError:
        return PER_PAGE
    return wanted if wanted in PER_PAGE_CHOICES else PER_PAGE


def issue_data(issue: Issue) -> dict:
    """The public information of an issue or pull request, for the JSON.

    Parameters:
        issue: The issue.

    Returns:
        The data.
    """
    return {
        "repository": issue.repository.full_name,
        "number": issue.number,
        "title": issue.title,
        "url": issue.url,
        "author": issue.author.login if issue.author else None,
        "status": issue.status,
        "created": issue.created.isoformat(),
        "closed": issue.closed.isoformat() if issue.closed else None,
        "merged": issue.merged.isoformat() if issue.merged else None,
    }


def table_address(columns: list[Column], size: int, saved: int | None = None) -> str:
    """The query of the table of pull requests with its columns of conditions and its size.

    Parameters:
        columns: The columns of conditions, in their order.
        size: The pull requests of a page.
        saved: The number of the saved filter that the table shows, None for none.

    Returns:
        Such as ``?col=branch~all~outdated&per_page=25``.
    """
    query = [("col", column.encode()) for column in columns] + [("per_page", size)]
    if saved:
        query.append(("saved", saved))
    return "?" + urlencode(query)


def saved_filter(project: Project, number: str | None) -> PullRequestFilter | None:
    """A saved filter of a project by its number.

    Parameters:
        project: The project.
        number: The number of the filter, such as from ``saved`` of the address; None or ""
            for none.

    Returns:
        The filter, None for none.

    Raises:
        FilterNotFound: The project has no filter of this number.
    """
    if not number:
        return None
    try:
        return project.filters.get(pk=int(number))
    except (ValueError, PullRequestFilter.DoesNotExist):
        raise FilterNotFound(str(number)) from None


def changed_columns(request: HttpRequest, columns: list[Column]) -> list[Column] | None:
    """The columns after a change that the menus of the table ask for, None without one.

    ``add`` adds the column of the form, ``edit=<i>`` replaces a column with it,
    ``filter_of=<i>&filter=<f>`` sets its filter, ``remove=<i>`` removes one and
    ``move=<i>&to=<j>`` moves one, such as by dragging it. A column keeps its AND
    (``Column.joined``) when it is changed; an AND of one column is none.

    Parameters:
        request: The request, with the fields of the menu.
        columns: The columns before.

    Returns:
        The columns after; None if the request changes nothing.

    Raises:
        ConditionError: The form is wrong: a subclass says how.
    """
    found = list(columns)
    changed = changes(request, found)
    return None if changed is None else Conjunction.normalized(changed)


def changes(request: HttpRequest, found: list[Column]) -> list[Column] | None:
    """The columns after a change of the menus of the table, see :func:`changed_columns`.

    Parameters:
        request: The request, with the fields of the menu.
        found: The columns before, a copy that is changed.

    Returns:
        The columns after; None if the request changes nothing.

    Raises:
        ConditionError: The form is wrong: a subclass says how.
    """

    def index(name: str) -> int:
        number = int(request.GET.get(name, "-1") or -1)
        if not 0 <= number < len(found):
            raise ConditionInputUnknown(f"{name}: {number}")
        return number

    try:
        if "add" in request.GET:
            return [*found, Column.of_form(request.GET)]
        if "edit" in request.GET:
            number = index("edit")
            # its AND and its NOT stay
            column = found[number]
            found[number] = replace(
                Column.of_form(request.GET), joined=column.joined, negated=column.negated
            )
            return found
        if "filter_of" in request.GET:  # a toggle of the check marks or crosses
            number = index("filter_of")
            filter = request.GET.get("filter", "all")
            if filter not in FILTERS:
                raise ConditionInputUnknown(f"filter: {filter}")
            found[number] = replace(found[number], filter=filter)
            return found
        if "remove" in request.GET:
            del found[index("remove")]
            return found
        if "move" in request.GET:
            column = found.pop(index("move"))
            found.insert(min(max(int(request.GET.get("to", 0)), 0), len(found)), column)
            return found
    except ValueError:
        raise ConditionInputUnknown(request.GET.urlencode()) from None
    return None


@require_http_methods(["GET", "HEAD"])
def project_pull_requests(request: HttpRequest, slug: str):
    """The pull requests of all repositories of a project together, public like the project.

    Columns of conditions, kept in the address (``col``), show whether each applies, and
    filter the pull requests; the menus of the table change them.

    Parameters:
        request: The request; ``page`` is the page of the list, ``per_page`` its size: 10, 25,
            50 or 100; ``col`` are the columns of conditions.
        slug: The project.

    Returns:
        The page or its JSON, or a redirect after a change of the columns.
    """
    access, moved = opened(request, slug, "pull-requests/")
    if moved:
        return moved
    size = per_page(request)
    saved = saved_filter(access.project, request.GET.get("saved"))
    values = request.GET.getlist("col")
    if saved and not values:  # a saved filter, opened from the tab Filters
        values = saved.columns
    columns = [Column.decode(value) for value in values]
    changed = changed_columns(request, columns)
    if changed is not None:
        address = table_address(changed, size, saved.pk if saved else None)
        return redirect(access.project.path("pull-requests/") + address)
    repositories = shown_repositories(access)
    results = ColumnResults(repositories, project=access.project)
    pages = Paginator(results.matching(columns), size)
    shown = pages.get_page(request.GET.get("page"))
    shown.object_list = results.rows(list(shown.object_list), columns)  # only this page
    labels = Label.objects.filter(repository__in=repositories).order_by("name")
    return page(
        request,
        "pycal_dashboard/project_pull_requests.html",
        {
            "project": access.project,
            "access": access,
            "rows": shown,
            "per_page": size,
            "per_page_choices": PER_PAGE_CHOICES,
            "columns": PULL_REQUEST_COLUMNS,
            "condition_columns": columns,
            "groups": GROUPS,
            "all_kinds": REVIEW_KINDS,
            "filters": FILTERS,
            "label_names": sorted({label.name for label in labels}),
            "label_colors": {label.name.lower(): label.color for label in labels},
            "address": table_address(columns, size, saved.pk if saved else None),
            "saved": saved,
            "adding": "new" in request.GET,  # the button New filter of the tab Filters
            "repositories": repositories,
            "tab": "pull-requests",
        },
        lambda: {
            "count": pages.count,
            "page": shown.number,
            "pages": pages.num_pages,
            "per_page": size,
            "columns": [column.encode() for column in columns],
            "pull_requests": [
                {**issue_data(row["pull"]), "conditions": [cell["result"] for cell in row["cells"]]}
                for row in shown
            ],
        },
    )


@login_required
@require_POST
def project_update(request: HttpRequest, slug: str):
    """Update a project from GitHub in the background.

    Parameters:
        request: The request.
        slug: The project.

    Returns:
        The page of the project, which shows the progress.
    """
    access = ProjectAccess.of(slug, request.user).require_update()
    UpdateQueue.add(access.project, request.user)
    return redirect(access.project.path())


@login_required
@require_http_methods(["GET", "POST"])
def project_edit(request: HttpRequest, slug: str):
    """Change the name, the description and whether the project is public, or delete it.

    Parameters:
        request: The request.
        slug: The project.

    Returns:
        The form, or the project after the change.
    """
    access, moved = opened(request, slug, "settings/")
    if moved:
        return moved
    access.require_write()
    project = access.project
    if request.method == "POST":
        editor = ProjectEditor(access)
        if "delete" in request.POST:
            access.require_owner()
            if request.POST.get("confirm") != "yes":
                messages.error(request, _("Tick the box to confirm that the project is deleted."))
                return redirect(project.path("settings/danger/"))
            editor.delete()
            messages.success(request, _("The project %(name)s is deleted.") % {"name": project})
            return redirect("projects")
        public = None  # writers keep it: their field is disabled, so it is not sent
        if "visibility" in request.POST or access.is_owner:
            public = request.POST.get("visibility", "public") == "public"
        editor.change(request.POST.get("name", ""), request.POST.get("description", ""), public)
        messages.success(request, _("The project is saved."))
        return redirect(project.path())
    form = {
        "name": project.name,
        "description": project.description,
        "public": project.public,
    }
    return render(
        request,
        "pycal_dashboard/project_form.html",
        {
            "form": form,
            "project": project,
            "access": access,
            "tab": "settings",
            "settings_tab": "display",
            "suggestion": ProjectEditor(access).suggestion() if access.is_owner else None,
            "old_slugs": project.slugs.exclude(slug=project.slug),
        },
    )


@login_required
@require_POST
def project_slug(request: HttpRequest, slug: str):
    """Give a project another address; the old one keeps leading to it.

    Parameters:
        request: The request, with ``slug`` and the page to go back to, ``back``.
        slug: The project.

    Returns:
        The page it came from, at the new address.
    """
    access = ProjectAccess.of(slug, request.user)
    if ProjectEditor(access).rename(request.POST.get("slug", "")):
        messages.success(
            request,
            _("The address of the project is %(path)s now; the old one leads to it.")
            % {"path": access.project.path()},
        )
    back = request.POST.get("back", "")
    return redirect(access.project.path(back if back in BACK_PAGES else "settings/"))


def person_client(request: HttpRequest) -> PersonClient:
    """GitHub with the token of the person who signed in.

    Parameters:
        request: The request.

    Returns:
        The client.

    Raises:
        GitHubTokenMissing: The site has no token of the person.
    """
    identity = GitHubIdentity.of(request.user)
    if identity is None:
        raise GitHubTokenMissing(str(request.user))
    return PersonClient.of(request.user, identity.login)


def known_repositories(user: AbstractBaseUser | AnonymousUser, text: str = "") -> list[str]:
    """The repositories the site knows that a person may add: public ones and their own.

    Parameters:
        user: The person.
        text: What they typed, "" for all.

    Returns:
        The full names, sorted.
    """
    mine = Q(projects__members__user=user) if getattr(user, "is_authenticated", False) else Q()
    found = Repository.objects.filter(Q(private=False) | mine)
    if text:
        found = found.filter(full_name__icontains=text)
    names = found.values_list("full_name", flat=True).distinct().order_by("full_name")
    return list(names[:KNOWN_CHOICES])


def add_repositories(request: HttpRequest, editor: ProjectEditor, names: list[str]) -> None:
    """Add repositories to a project, say what happened to each, and read the new ones.

    Parameters:
        request: The request, for the messages.
        editor: The editor of the project.
        names: The names or links of the repositories.
    """
    lookup = RepositoryLookup(person_client(request))
    added_any = False
    for name in names:
        try:
            repository = lookup.find(name)
            added = editor.add(repository)
        except DashboardError as error:
            messages.error(request, f"{error.title}: {error}")
            continue
        if added:
            added_any = True
            messages.success(request, _("%(name)s is added.") % {"name": repository})
        else:
            messages.info(request, _("%(name)s is in the project already.") % {"name": repository})
    if added_any:  # the data of the new repositories is read in the background
        UpdateQueue.add(editor.access.project, request.user, changed=True)


def choices(request: HttpRequest, owner: str, search: str) -> dict:
    """What the person chooses repositories from: their accounts, a list and search results.

    Errors of GitHub are shown on the page, so that the repositories can still be typed.

    Parameters:
        request: The request.
        owner: The account whose repositories are listed, "" for none.
        search: What the person searched for, "" for nothing.

    Returns:
        The context of the page.
    """
    context: dict = {"owner": owner, "search": search, "owners": [], "listed": [], "found": []}
    try:
        client = person_client(request)
        context["owners"] = [client.login, *client.organizations()]
        if owner:
            context["listed"] = client.repositories(owner)
        if search:
            known = known_repositories(request.user, search)
            context["found"] = known + [n for n in client.search(search) if n not in known]
    except Exception as exception:  # shown on the page, which still works
        context["github_error"] = translate(exception)
    return context


@login_required
@require_http_methods(["GET", "POST"])
def project_repositories(request: HttpRequest, slug: str):
    """Add and remove the repositories of a project, and install the GitHub App on them.

    Parameters:
        request: The request.
        slug: The project.

    Returns:
        The page.
    """
    access, moved = opened(request, slug, "settings/repositories/")
    if moved:
        return moved
    access.require_write()
    if request.method == "POST":
        editor = ProjectEditor(access)
        if "remove" in request.POST:
            removed = editor.remove(int(request.POST.get("remove") or 0))
            if removed:
                messages.success(request, _("%(name)s is removed.") % {"name": removed})
        else:
            names = request.POST.getlist("repository")
            add_repositories(request, editor, [n for n in names if n.strip()])
        return redirect(access.project.path("settings/repositories/"))
    owner = request.GET.get("owner", "").strip()
    search = request.GET.get("search", "").strip()
    repositories = list(access.project.repositories.select_related("installation"))
    return render(
        request,
        "pycal_dashboard/project_repositories.html",
        {
            "project": access.project,
            "access": access,
            "repositories": repositories,
            "without_app": [r for r in repositories if not r.app_installed],
            "outdated": [
                r for r in repositories if r.app_installed and r.installation.missing_permissions
            ],
            "known": known_repositories(request.user),
            "tab": "settings",
            "settings_tab": "repositories",
            "suggestion": ProjectEditor(access).suggestion() if access.is_owner else None,
            **choices(request, owner, search),
        },
    )


@login_required
@require_http_methods(["GET"])
def people_complete(request: HttpRequest):
    """The people whose GitHub handle or name is like what a person types: every such field.

    See :class:`~pycal_dashboard.services.handle_completion.HandleCompletion`: in a project
    (``project``), the authors of its pull requests first; then the people the site knows; then
    the accounts of GitHub. ``signed_in=1`` proposes only the people who signed in, who can get
    a role.

    Parameters:
        request: The request, with ``q``, and ``project`` and ``signed_in`` if any.

    Returns:
        The people as JSON: their GitHub handle (``login``), GitHub name and avatar; with
        ``error`` when GitHub could not be searched.

    Raises:
        ProjectNotFound: The person does not see the project.
    """
    slug = request.GET.get("project", "")
    access = ProjectAccess.of(slug, request.user) if slug else None
    completion = HandleCompletion(request.user, access, request.GET.get("signed_in") == "1")
    text = request.GET.get("q", "")
    people = completion.known(text)
    if completion.searches(text, people):
        try:
            people = completion.github(text, person_client(request), people)
        except DashboardError as error:
            return JsonResponse({"people": people, "error": error.code})
    return JsonResponse({"people": people})


@login_required
def repository_complete(request: HttpRequest):
    """The repositories whose name is like what a person types, for the field to add one.

    Parameters:
        request: The request, with ``q``.

    Returns:
        The names as JSON: those the site knows first, then those of GitHub.
    """
    text = request.GET.get("q", "").strip()
    if len(text) < MIN_SEARCH:
        return JsonResponse({"repositories": []})
    names = known_repositories(request.user, text)[:10]
    try:
        names += [n for n in person_client(request).search(text) if n not in names]
    except DashboardError as error:
        return JsonResponse({"repositories": names, "error": error.code})
    return JsonResponse({"repositories": names})


@login_required
@require_http_methods(["GET", "POST"])
def project_collaborators(request: HttpRequest, slug: str):
    """The collaborators of a project and their roles; owners share it and change the roles.

    Only writers and owners see the page, as the settings: readers and visitors do not.

    Parameters:
        request: The request.
        slug: The project.

    Returns:
        The page.

    Raises:
        ProjectReadOnly: The person may only read the project, or is none of its collaborators.
    """
    access, moved = opened(request, slug, "settings/collaborators/")
    if moved:
        return moved
    access.require_write()
    if request.method == "POST":
        editor = ProjectEditor(access)
        if "remove" in request.POST:
            member = editor.unshare(int(request.POST.get("remove") or 0))
            if member:
                messages.success(
                    request, _("@%(name)s has no role any more.") % {"name": name_of(member)}
                )
        else:
            member = editor.share(request.POST.get("github_name", ""), request.POST.get("role", ""))
            messages.success(
                request,
                _("@%(name)s may %(role)s the project.")
                % {"name": name_of(member), "role": role_title(member.role)},
            )
        return redirect(access.project.path("settings/collaborators/"))
    members = list(
        access.project.members.select_related("user__profile").order_by("user__username")
    )
    owners = [member for member in members if member.role == ProjectMember.OWNER]
    return render(
        request,
        "pycal_dashboard/project_collaborators.html",
        {
            "project": access.project,
            "access": access,
            "members": members,
            # a project always has an owner: the only one keeps the role and stays
            "only_owner": owners[0].pk if len(owners) == 1 else None,
            "roles": [(value, role_title(value)) for value, _title in ProjectMember.ROLES],
            "tab": "settings",
            "settings_tab": "collaborators",
        },
    )


def name_of(member: ProjectMember) -> str:
    """The GitHub name of a member of a project.

    Parameters:
        member: The member.

    Returns:
        The GitHub name, else the name of the account.
    """
    profile = getattr(member.user, "profile", None)
    return profile.github_name if profile and profile.github_name else member.user.username


def role_title(role: str) -> str:
    """The role as people read it.

    Parameters:
        role: ``read``, ``write`` or ``owner``.

    Returns:
        The translated title.
    """
    return {
        ProjectMember.READ: _("read"),
        ProjectMember.WRITE: _("change"),
        ProjectMember.OWNER: _("own"),
    }.get(role, role)


@login_required
@require_http_methods(["GET"])
def project_backup(request: HttpRequest, slug: str):
    """Download the backup of a project: its settings, repositories, filters and steps.

    Parameters:
        request: The request.
        slug: The project.

    Returns:
        The file of YAML.
    """
    access = ProjectAccess.of(slug, request.user).require_write()
    with IMPORT_GUARD:  # see import_guard.py: what makes YAML, only when needed
        from pycal_dashboard.services.project_backup import ProjectBackup

    answer = HttpResponse(
        ProjectBackup(access.project).export(), content_type="application/yaml; charset=utf-8"
    )
    day = timezone.now().date().isoformat()
    answer["Content-Disposition"] = (
        f'attachment; filename="{access.project.slug}-backup-{day}.yaml"'
    )
    return answer


@login_required
@require_POST
def project_restore(request: HttpRequest, slug: str):
    """Restore a project from a backup: first what it changes, then what the person ticked.

    The file ``backup`` shows the page of the plan
    (:class:`~pycal_dashboard.services.restore_plan.RestorePlan`), with the text of the file
    in the form. Restoring it (``backup_text``) makes what only adds, and of what deletes or
    replaces only what is ticked (``confirm``). The repositories of the backup that the
    project lacks are added as on the tab *Repositories*, with the rights of the person.

    Parameters:
        request: The request, with the file ``backup`` or the id of a ``snapshot``; or
            ``backup_text`` and ``confirm``.
        slug: The project.

    Returns:
        The page of the plan, or a redirect to the settings.

    Raises:
        ProjectOwnersOnly: Only the owners restore a backup: it can replace filters and steps.
        BackupInvalid: The file is no backup that the site can restore.
        BackupVersionUnknown: The backup has a version that the site does not know.
        SnapshotNotFound: The project has no snapshot of the id.
    """
    access = ProjectAccess.of(slug, request.user).require_owner()
    with IMPORT_GUARD:  # see import_guard.py
        from pycal_dashboard.services.project_backup import ProjectBackup
        from pycal_dashboard.services.restore_plan import RestorePlan

    if "backup_text" in request.POST:
        text = request.POST["backup_text"]
    elif "snapshot" in request.POST:  # a snapshot is restored as its backup
        text = SnapshotEditor(access).find(int(request.POST.get("snapshot") or 0)).text
    else:
        upload = request.FILES.get("backup")
        if upload is None:
            raise BackupInvalid("no file")
        try:
            text = upload.read(MAX_BACKUP + 1).decode("utf-8")
        except UnicodeDecodeError:
            raise BackupInvalid("not a text in UTF-8") from None
    plan = RestorePlan(access.project, ProjectBackup.read(text))
    if "backup_text" not in request.POST:
        return render(
            request,
            "pycal_dashboard/project_restore.html",
            {
                "project": access.project,
                "access": access,
                "tab": "settings",
                "text": text,
                "adds": [c for c in plan.changes if not c.confirm and not c.note],
                "asks": [change for change in plan.changes if change.confirm],
                "notes": [change for change in plan.changes if change.note],
            },
        )
    missing = plan.repositories
    for note in plan.apply(set(request.POST.getlist("confirm")), request.user):
        messages.warning(request, note)
    messages.success(request, _("The backup is restored."))
    if missing:
        add_repositories(request, ProjectEditor(access), missing)
    return redirect(access.project.path("settings/backup/"))
