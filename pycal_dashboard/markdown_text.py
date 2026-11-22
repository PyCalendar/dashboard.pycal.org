"""Markdown that people type, such as the description of a project, as safe HTML.

Every text that people type to describe something is Markdown: the filter ``|markdown`` of
``templatetags/markdown.py`` shows it, the partial ``_markdown_field.html`` edits it with a bar
and a preview, and the preview is made here too, so that it looks as the page will.
``tests/test_markdown.py`` checks the rules.

The HTML is cleaned (nh3): no scripts, styles or raw HTML of the text, links only to http,
https and mail, and every link with ``rel="nofollow noopener noreferrer"``. Images are shown
only from this site, such as the badges of pull requests: nothing is loaded from other sites.
An image of another site shows its text instead (:func:`foreign_image`), so that it is seen
where it is, such as a badge in a message.
"""

import html as html_text
import re
from functools import cache
from urllib.parse import urlsplit

from django.conf import settings
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext

from pycal_dashboard.import_guard import IMPORT_GUARD

# an item of a list of tasks as GitHub writes it: - [ ] or - [x], also in a paragraph of its own
TASK = re.compile(r"<li>(\s*<p>)?\[( |x|X)\] ")
# an image whose address was removed: it shows nothing
EMPTY_IMAGE = re.compile(r"<img(?![^>]*\ssrc=)[^>]*>")
# an image as the parser writes it, before the HTML is cleaned
IMAGE = re.compile(r'<img src="([^"]*)" alt="([^"]*)"(?: title="[^"]*")? />')

# the elements and attributes that the HTML of Markdown may have
TAGS = {
    "a", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr",
    "li", "ol", "p", "pre", "s", "strong", "table", "tbody", "td", "th", "thead", "tr", "ul",
    "img", "span",
}  # fmt: skip
ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "th": {"align"},
    "td": {"align"},
    "span": {"class", "title"},  # only of foreign_image(): the parser writes no raw HTML
    "ol": {"start"},
}
SCHEMES = {"http", "https", "mailto"}


@cache
def parser():
    """The parser of CommonMark with tables and strikethrough, without raw HTML."""
    with IMPORT_GUARD:  # see import_guard.py
        from markdown_it import MarkdownIt

    return MarkdownIt("commonmark", {"html": False, "linkify": False}).enable(
        ["table", "strikethrough"]
    )


def own_images(element: str, attribute: str, value: str) -> str | None:
    """Keep the images of this site only, such as the badges of pull requests.

    An image of another site would load it when the page is shown, which the site never does
    (see the privacy policy): its address is removed. The address of this site becomes a path.

    Parameters:
        element: The element, such as ``img``.
        attribute: The attribute, such as ``src``.
        value: Its value.

    Returns:
        The value; the path of an image of this site; None to remove the attribute.

    Examples:
        >>> own_images("img", "src", "https://evil.example/x.png") is None
        True
        >>> own_images("a", "href", "https://pycal.org")
        'https://pycal.org'
    """
    if element != "img" or attribute != "src":
        return value
    site = settings.SITE_URL.rstrip("/") + "/"
    if value.startswith(site):
        return "/" + value[len(site) :]
    if value.startswith("/") and not value.startswith("//"):
        return value
    return None


def foreign_image(match: re.Match) -> str:
    """An image of another site as its text, which says why it is not shown; others stay.

    Parameters:
        match: An image of the HTML of the parser: its address and its text.

    Returns:
        The image of this site as it is; else its text, or that of its site, as a ``span``.

    Examples:
        >>> found = IMAGE.search('<img src="https://x.example/b.svg" alt="Badge" />')
        >>> foreign_image(found).endswith('">Badge</span>')
        True
    """
    address = html_text.unescape(match[1])
    if own_images("img", "src", address) is not None:
        return match[0]
    host = urlsplit(address).hostname or ""
    title = gettext(
        "An image of %(host)s, which %(site_name)s does not load: nothing is loaded from other "
        "sites."
    ) % {"host": host, "site_name": settings.SITE_NAME}
    text = match[2] or gettext("Image of %(host)s") % {"host": host}
    return f'<span class="foreign-image" title="{html_text.escape(title)}">{text}</span>'


def task_box(match: re.Match) -> str:
    """An item of a list of tasks with a checkbox, as GitHub shows it: checked or not, fixed.

    Parameters:
        match: The start of the item and its ``[ ]`` or ``[x]``.

    Returns:
        The start of the item with a checkbox that cannot be changed.

    Examples:
        >>> TASK.sub(task_box, "<li>[x] done</li>")
        '<li class="task-item"><input type="checkbox" class="task-box" disabled checked> done</li>'
    """
    checked = " checked" if match[2].lower() == "x" else ""
    box = f'<input type="checkbox" class="task-box" disabled{checked}>'
    return f'<li class="task-item">{match[1] or ""}{box} '


def render(text: str) -> SafeString:
    """The HTML of a text in Markdown, cleaned.

    Parameters:
        text: The Markdown, such as ``**bold** and [a link](https://pycal.org)``.

    Returns:
        The HTML, safe to show; empty for an empty text.

    Examples:
        >>> render("**bold**")
        '<p><strong>bold</strong></p>'
        >>> render("<script>alert(1)</script>")
        '<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>'
    """
    if not text or not text.strip():
        return mark_safe("")  # noqa: S308 - nothing
    with IMPORT_GUARD:  # see import_guard.py
        import nh3

    html = nh3.clean(
        IMAGE.sub(foreign_image, parser().render(text)),
        tags=TAGS,
        attributes=ATTRIBUTES,
        url_schemes=SCHEMES,
        link_rel="nofollow noopener noreferrer",
        attribute_filter=own_images,
    )
    html = EMPTY_IMAGE.sub("", html)
    html = TASK.sub(task_box, html)
    return mark_safe(html.strip())  # noqa: S308 - cleaned by nh3
