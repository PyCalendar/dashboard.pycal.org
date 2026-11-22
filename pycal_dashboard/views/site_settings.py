"""The page Settings of the administrators: the hosts whose images texts of Markdown show."""

from __future__ import annotations

import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from pycal_dashboard.actions import ImageHostsSaved, Trigger
from pycal_dashboard.errors import ImageHostInvalid
from pycal_dashboard.models import SiteSettings
from pycal_dashboard.services.identity import GitHubIdentity

# the name of a host: labels of letters, digits and hyphens, separated by dots; *. before it
# stands for all hosts below it, such as *.pycal.org, which needs two labels at least
HOST = re.compile(r"(\*\.)?(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
MAX_HOSTS = 50


def image_hosts(text: str) -> list[str]:
    r"""The hosts of a text, one a line, checked.

    Parameters:
        text: The text of the form; ``https://`` and a slash at the end are taken away.
            ``*.pycal.org`` stands for all hosts below pycal.org, not pycal.org itself.

    Returns:
        The hosts in lower case, each once, in their order.

    Raises:
        ImageHostInvalid: A line is not the name of a host, or there are too many.

    Examples:
        >>> image_hosts("Insight.pycal.org\n\nhttps://img.shields.io/\ninsight.pycal.org")
        ['insight.pycal.org', 'img.shields.io']
        >>> image_hosts("*.pycal.org")
        ['*.pycal.org']
    """
    hosts: list[str] = []
    for line in text.splitlines():
        host = line.strip().lower().removeprefix("https://").rstrip("/")
        if not host:
            continue
        if not HOST.fullmatch(host):
            raise ImageHostInvalid(line.strip()[:100])
        if host not in hosts:
            hosts.append(host)
    if len(hosts) > MAX_HOSTS:
        raise ImageHostInvalid(f"at most {MAX_HOSTS} hosts")
    return hosts


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def site_settings(request: HttpRequest):
    """The settings of the site, for its administrators (``SITE_ADMINS``).

    Parameters:
        request: The request; POST with ``image_hosts``, one host a line.

    Returns:
        The page, or after saving a redirect to it.

    Raises:
        PermissionDenied: The person is not in ``SITE_ADMINS``.
    """
    if not GitHubIdentity.is_site_admin(request.user):
        raise PermissionDenied("the settings are for the administrators")
    found = SiteSettings.current()
    text = "\n".join(found.image_hosts)
    if request.method == "POST":
        text = request.POST.get("image_hosts", "")
        try:
            hosts = image_hosts(text)
        except ImageHostInvalid as error:
            messages.error(request, f"{error.title}: {error}")
        else:
            found.image_hosts = hosts
            identity = GitHubIdentity.of(request.user)
            actor = identity.login if identity else request.user.username
            with Trigger.start("setup", "Settings of the site saved", actor_login=actor):
                found.save()
                ImageHostsSaved(hosts).run()
            messages.success(request, _("The settings are saved."))
            return redirect("site_settings")
    return render(request, "pycal_dashboard/site_settings.html", {"image_hosts": text})
