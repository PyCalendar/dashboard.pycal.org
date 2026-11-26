"""Links to GitHub with the mark of GitHub.

``{% github_link url label %}`` is the mark alone, for places where it is clear what it links
to, such as next to the title of a repository; ``label`` is its text for screen readers and
on hover. ``{% github_link url label text "button" %}`` shows the mark before ``text``.
``{% github_mark url %}`` is the mark at the end of a link of a template that leads to GitHub.
``{% github_user person %}`` shows a person: their GitHub handle leads to their page on the
dashboard, the mark of GitHub after it to their profile on GitHub.
"""

from django import template
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from pycal_dashboard.github_mark import leads_to_github, svg
from pycal_dashboard.import_guard import IMPORT_GUARD
from pycal_dashboard.models import GitHubUser

register = template.Library()


def mark() -> str:
    """The mark of GitHub as inline SVG, in the color of the text.

    Returns:
        The HTML, hidden from screen readers: the link has the label.
    """
    return mark_safe(svg())  # noqa: S308 - a constant


@register.simple_tag
def github_mark(url: str) -> str:
    """The mark of GitHub at the end of a link that leads to GitHub, such as of a repository.

    Every link to GitHub has the mark, so that people see that they leave the site; this one
    goes into a link of a template, after its text: ``<a href="{{ url }}">{{ text }}{%
    github_mark url %}</a>``.

    Parameters:
        url: The address of the link.

    Returns:
        A space and the mark for an address on GitHub; "" for another one.
    """
    return mark_safe(" " + svg()) if leads_to_github(str(url or "")) else ""  # noqa: S308


@register.simple_tag
def github_link(url: str, label: str, text: str = "", css: str = "") -> str:
    """A link to GitHub with its mark.

    Parameters:
        url: The address on GitHub.
        label: What the link leads to, such as ``PyCalendar/icalendar on GitHub``.
        text: The visible text after the mark; "" for the mark alone.
        css: More classes of the link, such as ``button``.

    Returns:
        The HTML of the link; empty without an address.
    """
    if not url:
        return ""
    classes = f"github-link {css}".strip()
    if text:
        return format_html(
            '<a class="{}" href="{}" title="{}">{} <span>{}</span></a>',
            classes,
            url,
            label,
            mark(),
            text,
        )
    return format_html(
        '<a class="{} github-link-icon" href="{}" aria-label="{}" title="{}">{}</a>',
        classes,
        url,
        label,
        label,
        mark(),
    )


def avatar_url(person: GitHubUser | str, size: int) -> str:
    """The address of the avatar on GitHub, in the size shown, for twice as many pixels.

    Parameters:
        person: A ``GitHubUser``, or a GitHub name.
        size: The width shown, in CSS pixels.

    Returns:
        The address on avatars.githubusercontent.com, or that of the GitHub user.

    Examples:
        >>> avatar_url("octocat", 20)
        'https://avatars.githubusercontent.com/octocat?s=40'
    """
    login = getattr(person, "login", None) or str(person)
    url = getattr(person, "avatar_url", "") or f"https://avatars.githubusercontent.com/{login}"
    return f"{url}{'&' if '?' in url else '?'}s={2 * size}"


@register.inclusion_tag("pycal_dashboard/_github_user.html", takes_context=True)
def github_user(
    context: template.Context,
    person: GitHubUser | str | None,
    size: int = 20,
    name: str = "",
    href: str = "",
) -> dict:
    """A person of GitHub: their avatar before their GitHub handle, then the mark of GitHub.

    The GitHub handle leads to the page of the person on the dashboard: in a project (the
    ``project`` of the page), to their page in the project, else to their page in all projects;
    the mark of GitHub after it leads to their profile on GitHub.

    Parameters:
        context: The context of the page, with its ``project``, if any.
        person: A ``GitHubUser``, a GitHub handle, or None when GitHub does not say who.
        size: The width of the avatar, in CSS pixels.
        name: A full name to show after the GitHub handle; "" for none: the pages show the
            GitHub handle alone.
        href: Another address to link the GitHub handle to; "" for the page of the person.

    Returns:
        The context of the partial.
    """
    login = getattr(person, "login", None) or (str(person) if person else "")
    if login and not href:
        project = context.get("project")
        if isinstance(getattr(project, "slug", None), str):
            href = reverse("project_contributor", args=[project.slug, login])
        else:
            href = reverse("person", args=[login])
    return {
        "login": login,
        "href": href,
        "github": f"https://github.com/{login}",
        "name": name,
        "avatar": avatar_url(person, size) if login else "",
        "size": size,
    }


@register.inclusion_tag("pycal_dashboard/_permission_list.html")
def permission_list(permissions: dict | None, events: list | None = None) -> dict:
    """Permissions and events as the settings of the GitHub App on GitHub name them.

    Parameters:
        permissions: Permissions by the names of the API, with their level.
        events: Events by the names of the API.

    Returns:
        The context of the partial: the groups.
    """
    with IMPORT_GUARD:  # see import_guard.py; only the pages of permissions need the names
        from pycal_dashboard.github.permission_names import grouped

    return {"groups": grouped(dict(permissions or {}), list(events or []))}
