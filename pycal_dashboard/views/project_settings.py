"""The tabs of the settings of a project: Snapshots, Backup and Danger zone.

Display (``project_edit``) and Collaborators (``project_collaborators``) are in
:mod:`pycal_dashboard.views.projects`; all tabs share the row ``_settings_tabs.html``.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from pycal_dashboard.services.snapshot_editor import SnapshotEditor

from .projects import opened


@login_required
@require_http_methods(["GET", "HEAD"])
def project_backup_page(request: HttpRequest, slug: str):
    """Backup: download the backup of the project, and restore one, for the owners.

    Parameters:
        request: The request.
        slug: The project.

    Returns:
        The page.

    Raises:
        ProjectReadOnly: Only writers and owners see the settings.
    """
    access, moved = opened(request, slug, "settings/backup/")
    if moved:
        return moved
    access.require_write()
    context = {"project": access.project, "access": access, "tab": "settings"}
    return render(
        request, "pycal_dashboard/project_backup.html", context | {"settings_tab": "backup"}
    )


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def project_snapshots(request: HttpRequest, slug: str):
    """Snapshots: take one, and the list of all, to download, restore or delete.

    Parameters:
        request: The request; POST with ``take``, or ``delete`` and the id of a snapshot.
        slug: The project.

    Returns:
        The page, or after POST a redirect to it.

    Raises:
        ProjectReadOnly: Only writers and owners see the snapshots and take them.
        ProjectOwnersOnly: Only the owners delete a snapshot.
        SnapshotNotFound: The project has no snapshot to delete of the id.
    """
    access, moved = opened(request, slug, "settings/snapshots/")
    if moved:
        return moved
    access.require_write()
    editor = SnapshotEditor(access)
    if request.method == "POST":
        if "delete" in request.POST:
            editor.delete(int(request.POST.get("delete") or 0))
            messages.success(request, _("The snapshot is deleted."))
        else:
            editor.take()
            messages.success(request, _("The snapshot is taken."))
        return redirect(access.project.path("settings/snapshots/"))
    snapshots = access.project.snapshots.select_related("created_by__profile").defer("text")
    return render(
        request,
        "pycal_dashboard/project_snapshots.html",
        {
            "project": access.project,
            "access": access,
            "tab": "settings",
            "settings_tab": "snapshots",
            "snapshots": snapshots,
        },
    )


@login_required
@require_http_methods(["GET"])
def project_snapshot_download(request: HttpRequest, slug: str, pk: int):
    """Download a snapshot: the file of a backup, restored as one.

    Parameters:
        request: The request.
        slug: The project.
        pk: The id of the snapshot.

    Returns:
        The file of YAML.

    Raises:
        ProjectReadOnly: Only writers and owners download snapshots.
        SnapshotNotFound: The project has no such snapshot.
    """
    access, moved = opened(request, slug, f"settings/snapshots/{pk}/download/")
    if moved:
        return moved
    editor = SnapshotEditor(access)
    snapshot = editor.find(pk)
    answer = HttpResponse(snapshot.text, content_type="application/yaml; charset=utf-8")
    answer["Content-Disposition"] = f'attachment; filename="{editor.filename(snapshot)}"'
    return answer


@login_required
@require_http_methods(["GET", "HEAD"])
def project_danger(request: HttpRequest, slug: str):
    """Danger zone: delete the project, for the owners.

    Parameters:
        request: The request.
        slug: The project.

    Returns:
        The page; the form deletes on the page Display (``project_edit``).

    Raises:
        ProjectReadOnly: Only writers and owners see the settings.
    """
    access, moved = opened(request, slug, "settings/danger/")
    if moved:
        return moved
    access.require_write()
    return render(
        request,
        "pycal_dashboard/project_danger.html",
        {"project": access.project, "access": access, "tab": "settings", "settings_tab": "danger"},
    )
