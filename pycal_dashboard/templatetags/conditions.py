"""``{% label_color colors name %}``: the color of a label in the columns of conditions."""

from django import template

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
