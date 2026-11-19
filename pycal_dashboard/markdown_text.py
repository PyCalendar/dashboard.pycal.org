"""Markdown that people type, such as the description of a project, as safe HTML.

Every text that people type to describe something is Markdown: the filter ``|markdown`` of
``templatetags/markdown.py`` shows it, the partial ``_markdown_field.html`` edits it with a bar
and a preview, and the preview is made here too, so that it looks as the page will.
``tests/test_markdown.py`` checks the rules.

The HTML is cleaned (nh3): no scripts, styles or raw HTML of the text, links only to http,
https and mail, and every link with ``rel="nofollow noopener noreferrer"``.
"""

from functools import cache

from django.utils.safestring import SafeString, mark_safe

from pycal_dashboard.import_guard import IMPORT_GUARD

# the elements and attributes that the HTML of Markdown may have
TAGS = {
    "a", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr",
    "li", "ol", "p", "pre", "s", "strong", "table", "tbody", "td", "th", "thead", "tr", "ul",
}  # fmt: skip
ATTRIBUTES = {"a": {"href", "title"}, "th": {"align"}, "td": {"align"}, "ol": {"start"}}
SCHEMES = {"http", "https", "mailto"}


@cache
def parser():
    """The parser of CommonMark with tables and strikethrough, without raw HTML."""
    with IMPORT_GUARD:  # see import_guard.py
        from markdown_it import MarkdownIt

    return MarkdownIt("commonmark", {"html": False, "linkify": False}).enable(
        ["table", "strikethrough"]
    )


def render(text: str) -> SafeString:
    """The HTML of a text in Markdown, cleaned.

    Args:
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
        parser().render(text),
        tags=TAGS,
        attributes=ATTRIBUTES,
        url_schemes=SCHEMES,
        link_rel="nofollow noopener noreferrer",
    )
    return mark_safe(html.strip())  # noqa: S308 - cleaned by nh3
