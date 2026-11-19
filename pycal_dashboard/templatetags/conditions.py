"""``{% label_color colors name %}``: the color of a label in the columns of conditions."""

from django import template

from pycal_dashboard.conditions.group.column import Column

register = template.Library()

# a label that no repository has yet: grey, as GitHub shows new labels
DEFAULT = "ededed"


@register.simple_tag
def label_color(colors: dict[str, str], name: str) -> str:
    """The color of a label of the repositories, as GitHub writes it, without ``#``.

    Parameters:
        colors: The colors by the names of the labels, in small letters.
        name: The name of the label, in any case.

    Returns:
        Such as ``d73a4a``; grey for a label that no repository has.

    Examples:
        >>> label_color({"bug": "d73a4a"}, "Bug")
        'd73a4a'
        >>> label_color({}, "new")
        'ededed'
    """
    color = (colors or {}).get(name.lower(), "")
    return (
        color if len(color) == 6 and all(c in "0123456789abcdefABCDEF" for c in color) else DEFAULT
    )


@register.filter
def toggled(column: Column, result: str) -> str:
    """The filter of a column after a click on one of its toggles, see ``Column.toggled``.

    Parameters:
        column: The column.
        result: ``applies`` for the check marks, ``not`` for the crosses.

    Returns:
        The filter.
    """
    return column.toggled(result)


@register.filter
def shown_filter(column: Column, result: str) -> bool:
    """Whether a toggle of a column is on, see ``Column.shown``.

    Parameters:
        column: The column.
        result: ``applies`` or ``not``.

    Returns:
        True if it is on.
    """
    return column.shown(result)
