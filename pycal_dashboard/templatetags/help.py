"""Links to the documentation next to things: an open book.

``{% help_link url label %}`` opens the page of the documentation in a new tab; ``label`` says
what it explains, for screen readers and on hover.
"""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext

register = template.Library()

# an open book, drawn with the color of the text: the two pages and their spine
BOOK = mark_safe(  # noqa: S308 - a constant
    '<svg class="icon book" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" '
    'focusable="false" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 7c-1.5-1.6-4-2.5-9-2.5v13c5 0 7.5.9 9 2.5 1.5-1.6 4-2.5 9-2.5v-13c-5 0-7.5.9-9 '
    '2.5z"/><path d="M12 7v13"/></svg>'
)


@register.simple_tag
def help_link(url: str, label: str) -> str:
    """A link to the documentation as an open book, opening a new tab.

    Args:
        url: The page of the documentation.
        label: What the page explains, such as ``Email for new permissions``.

    Returns:
        The HTML of the link; empty without an address.
    """
    if not url:
        return ""
    title = gettext("Help: %(label)s (opens in a new tab)") % {"label": label}
    return format_html(
        '<a class="help-link" href="{}" target="_blank" rel="noopener" title="{}" '
        'aria-label="{}">{}</a>',
        url,
        title,
        title,
        BOOK,
    )
