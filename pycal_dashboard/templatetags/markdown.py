"""``{{ text|markdown }}``: a text that people typed, shown as Markdown.

See :mod:`pycal_dashboard.markdown_text`; the partial ``_markdown_field.html`` edits such a text.
"""

from django import template

from pycal_dashboard.markdown_text import render

register = template.Library()


@register.filter(name="markdown")
def markdown(text: str):
    """The HTML of a text in Markdown, cleaned.

    Parameters:
        text: The Markdown.

    Returns:
        The safe HTML.
    """
    return render(text or "")
