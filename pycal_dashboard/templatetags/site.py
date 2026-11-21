"""The name of the site in texts that name it, such as those of the privacy policy."""

from __future__ import annotations

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def named(text: object) -> str:
    """A text with the name of the site in place of ``%(site_name)s``.

    Texts of the code name the site so, as the templates name it ``{{ site_name }}``: the
    site names itself by its name, never "this site".

    Parameters:
        text: The text, translated.

    Returns:
        The text with the name, such as ``dashboard.pycal.org``.

    Examples:
        >>> from django.conf import settings
        >>> named("Run by %(site_name)s.") == f"Run by {settings.SITE_NAME}."
        True
    """
    text = str(text)
    return text % {"site_name": settings.SITE_NAME} if "%(site_name)s" in text else text
