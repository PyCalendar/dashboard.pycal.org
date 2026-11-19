"""The projects: the public list, the overview of a project, and the pages that change it."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from pycal_dashboard.errors import DashboardError, GitHubTokenMissing, ProjectNotFound, translate
from pycal_dashboard.github.person_client import PersonClient
from pycal_dashboard.models import GitHubUser, Issue, ProjectMember, Repository
from pycal_dashboard.services.identity import GitHubIdentity
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.project_status import ProjectStatus
from pycal_dashboard.services.repository_lookup import RepositoryLookup
from pycal_dashboard.services.update_queue import UpdateQueue
from pycal_dashboard.services.update_worker import UpdateWorker
from pycal_dashboard.templatetags.github import avatar_url

from .json_page import page

# the pages that a change of the address goes back to
BACK_PAGES = {"settings/", "repositories/"}
# the repositories offered while typing, of those the site knows
KNOWN_CHOICES = 200
MIN_SEARCH = 2


def shown_repositories(access: ProjectAccess) -> list[Repository]:
    """The repositories of a project that a person sees.

    A public project may contain a repository that became private after it was added: only the
    collaborators of the project see it.

    Args:
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

    Args:
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
            }
            for r in repositories
        ],
    }


def access_url(project) -> str:
    """The path of the page of a project.

    Args:
        project: The project.

    Returns:
        The path.
    """
    return project.path()


def opened(request, slug: str, page: str = ""):
    """The project of an address, and where to go if it has another address now.

    Args:
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

    Args:
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


def projects(request):
    """The projects that the visitor sees: all public ones, and private ones of their own.

    Args:
        request: The request.

    Returns:
        The page or ``/projects.json``.
    """
    found = list(ProjectAccess.visible(request.user).prefetch_related("repositories"))
    return page(
        request,
        "pycal_dashboard/projects.html",
        {"projects": found},
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
def project_new(request):
    """Create a project: its name, description and whether it is public.

    Args:
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
        return redirect(project.path("repositories/"))
    return render(request, "pycal_dashboard/project_form.html", {"form": form, "new": True})


PAGES = {"": "", "update": "", "settings": "settings/", "address": "settings/"}
PAGES |= {"repositories": "repositories/", "collaborators": "collaborators/"}
PAGES["pull-requests"] = "pull-requests/"
PAGES["people"] = "collaborators/"  # the tab before it was called Collaborators


def project_moved(request, slug: str, name: str = "", page: str = ""):
    """An address of a project from before: with its name after the slug, or the tab People.

    Args:
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


def project(request, slug: str):
    """The overview of a project: its repositories with their open issues and pull requests.

    Args:
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
        },
        lambda: project_data(access, repositories),
    )


PULL_REQUEST_STATES = {"all", "open", "merged", "closed"}
PER_PAGE = 50


def pull_requests_of(repositories: list[Repository], state: str):
    """The pull requests of repositories together, the newest first.

    Args:
        repositories: The repositories that the person sees.
        state: ``all``, ``open``, ``merged`` or ``closed`` (closed without merging).

    Returns:
        The query of the pull requests.
    """
    found = (
        Issue.objects.filter(repository__in=repositories, pull_request=True)
        .select_related("author", "repository")
        .order_by("-created", "-pk")
    )
    if state == "open":
        found = found.filter(state=Issue.OPEN)
    elif state == "merged":
        found = found.filter(merged__isnull=False)
    elif state == "closed":
        found = found.filter(state=Issue.CLOSED, merged__isnull=True)
    return found


def issue_data(issue: Issue) -> dict:
    """The public information of an issue or pull request, for the JSON.

    Args:
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


@require_http_methods(["GET", "HEAD"])
def project_pull_requests(request, slug: str):
    """The pull requests of all repositories of a project together, public like the project.

    Args:
        request: The request; ``state`` filters, ``page`` is the page of the list.
        slug: The project.

    Returns:
        The page or its JSON.
    """
    access, moved = opened(request, slug, "pull-requests/")
    if moved:
        return moved
    state = request.GET.get("state", "all")
    if state not in PULL_REQUEST_STATES:
        state = "all"
    repositories = shown_repositories(access)
    pages = Paginator(pull_requests_of(repositories, state), PER_PAGE)
    shown = pages.get_page(request.GET.get("page"))
    return page(
        request,
        "pycal_dashboard/project_pull_requests.html",
        {
            "project": access.project,
            "access": access,
            "pull_requests": shown,
            "state": state,
            "states": [
                ("all", _("All")),
                ("open", _("Open")),
                ("merged", _("Merged")),
                ("closed", _("Closed")),
            ],
            "repositories": repositories,
            "tab": "pull-requests",
        },
        lambda: {
            "state": state,
            "count": pages.count,
            "page": shown.number,
            "pages": pages.num_pages,
            "pull_requests": [issue_data(issue) for issue in shown],
        },
    )


@login_required
@require_POST
def project_update(request, slug: str):
    """Update a project from GitHub in the background.

    Args:
        request: The request.
        slug: The project.

    Returns:
        The page of the project, which shows the progress.
    """
    access = ProjectAccess.of(slug, request.user).require_write()
    UpdateQueue.add(access.project, request.user)
    return redirect(access.project.path())


@login_required
@require_http_methods(["GET", "POST"])
def project_edit(request, slug: str):
    """Change the name, the description and whether the project is public, or delete it.

    Args:
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
                return redirect(project.path("settings/"))
            editor.delete()
            messages.success(request, _("The project %(name)s is deleted.") % {"name": project})
            return redirect("projects")
        public = None
        if access.is_owner:
            public = request.POST.get("visibility", "public") == "public"
        editor.change(request.POST.get("name", ""), request.POST.get("description", ""), public)
        messages.success(request, _("The project is saved."))
        return redirect(project.path())
    form = {"name": project.name, "description": project.description, "public": project.public}
    return render(
        request,
        "pycal_dashboard/project_form.html",
        {
            "form": form,
            "project": project,
            "access": access,
            "tab": "settings",
            "suggestion": ProjectEditor(access).suggestion() if access.is_owner else None,
            "old_slugs": project.slugs.exclude(slug=project.slug),
        },
    )


@login_required
@require_POST
def project_slug(request, slug: str):
    """Give a project another address; the old one keeps leading to it.

    Args:
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


def person_client(request) -> PersonClient:
    """GitHub with the token of the person who signed in.

    Args:
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


def known_repositories(user, text: str = "") -> list[str]:
    """The repositories the site knows that a person may add: public ones and their own.

    Args:
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


def add_repositories(request, editor: ProjectEditor, names: list[str]) -> None:
    """Add repositories to a project, say what happened to each, and read the new ones.

    Args:
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


def choices(request, owner: str, search: str) -> dict:
    """What the person chooses repositories from: their accounts, a list and search results.

    Errors of GitHub are shown on the page, so that the repositories can still be typed.

    Args:
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
def project_repositories(request, slug: str):
    """Add and remove the repositories of a project, and install the GitHub App on them.

    Args:
        request: The request.
        slug: The project.

    Returns:
        The page.
    """
    access, moved = opened(request, slug, "repositories/")
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
        return redirect(access.project.path("repositories/"))
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
            "tab": "repositories",
            "suggestion": ProjectEditor(access).suggestion() if access.is_owner else None,
            **choices(request, owner, search),
        },
    )


@login_required
@require_http_methods(["GET"])
def people_complete(request):
    """The people whose GitHub name is like what an owner types, to share a project with them.

    Only people who signed in to the site can get a role, so only they are proposed.

    Args:
        request: The request, with ``q``.

    Returns:
        The people as JSON: their GitHub name, full name and avatar.
    """
    text = request.GET.get("q", "").strip().removeprefix("@")
    if not text:
        return JsonResponse({"people": []})
    found = (
        GitHubUser.objects.filter(user__isnull=False)
        .filter(Q(login__istartswith=text) | Q(name__icontains=text))
        .order_by("login")[:10]
    )
    return JsonResponse(
        {
            "people": [
                {"login": person.login, "name": person.name, "avatar": avatar_url(person, 20)}
                for person in found
            ]
        }
    )


@login_required
def repository_complete(request):
    """The repositories whose name is like what a person types, for the field to add one.

    Args:
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
def project_collaborators(request, slug: str):
    """The collaborators of a project and their roles; owners share it and change the roles.

    Args:
        request: The request.
        slug: The project.

    Returns:
        The page.
    """
    access, moved = opened(request, slug, "collaborators/")
    if moved:
        return moved
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
        return redirect(access.project.path("collaborators/"))
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
            "tab": "collaborators",
        },
    )


def name_of(member: ProjectMember) -> str:
    """The GitHub name of a member of a project.

    Args:
        member: The member.

    Returns:
        The GitHub name, else the name of the account.
    """
    profile = getattr(member.user, "profile", None)
    return profile.github_name if profile and profile.github_name else member.user.username


def role_title(role: str) -> str:
    """The role as people read it.

    Args:
        role: ``read``, ``write`` or ``owner``.

    Returns:
        The translated title.
    """
    return {
        ProjectMember.READ: _("read"),
        ProjectMember.WRITE: _("change"),
        ProjectMember.OWNER: _("own"),
    }.get(role, role)
