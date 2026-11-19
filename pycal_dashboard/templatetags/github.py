"""Links to GitHub with the mark of GitHub.

``{% github_link url label %}`` is the mark alone, for places where it is clear what it links
to, such as next to the title of a repository; ``label`` is its text for screen readers and
on hover. ``{% github_link url label text "button" %}`` shows the mark before ``text``.
"""

from django import template
from django.utils.html import format_html

from pycal_dashboard.github_mark import PATH

register = template.Library()


def mark() -> str:
    """The mark of GitHub as inline SVG, in the color of the text.

    Returns:
        The HTML, hidden from screen readers: the link has the label.
    """
    return format_html(
        '<svg class="icon github-mark" viewBox="0 0 16 16" width="16" height="16" '
        'aria-hidden="true" focusable="false"><path fill="currentColor" d="{}"/></svg>',
        PATH,
    )


@register.simple_tag
def github_link(url: str, label: str, text: str = "", css: str = "") -> str:
    """A link to GitHub with its mark.

    Args:
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


def avatar_url(person, size: int) -> str:
    """The address of the avatar on GitHub, in the size shown, for twice as many pixels.

    Args:
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


@register.inclusion_tag("pycal_dashboard/_github_user.html")
def github_user(person, size: int = 20, name: str = "") -> dict:
    """A person of GitHub: their avatar from GitHub before their name, linked to GitHub.

    Args:
        person: A ``GitHubUser``, a GitHub name, or None when GitHub does not say who.
        size: The width of the avatar, in CSS pixels.
        name: Their full name, shown after the GitHub name; "" for none, or the name of the
            GitHub user.

    Returns:
        The context of the partial.
    """
    login = getattr(person, "login", None) or (str(person) if person else "")
    return {
        "login": login,
        "name": name or getattr(person, "name", ""),
        "avatar": avatar_url(person, size) if login else "",
        "size": size,
    }
