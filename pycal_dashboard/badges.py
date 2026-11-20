"""Flat badges as SVG, drawn by anybadge as in community-insights, and as PNG.

anybadge and Pillow are imported when a badge is drawn, through the import guard: the pages of
every day do not load them.
"""

from __future__ import annotations

import hashlib
import io
import re
from xml.sax.saxutils import escape, quoteattr

from pycal_dashboard.import_guard import IMPORT_GUARD

# anybadge 1.18 and newer write a role, a label and a title of their own: the same attributes
# twice make the SVG invalid, so theirs are replaced by those of svg()
OWN_TITLE = re.compile(r"\s*<title>[^<]*</title>")
OWN_NAME = re.compile(r' (?:role|aria-label)="[^"]*"')
LABEL_COLOR = "#555555"
SCALE = 2  # the PNG is drawn twice as large, for sharp screens
HEIGHT = 20
PADDING = 6
FONT_SIZE = 11


def svg(label: str, value: str, color: str) -> bytes:
    """A flat SVG badge: the label on grey, the value on the color.

    anybadge measures the text, so long and short texts fit; the badge gets one title and one
    label for screen readers. The id of its mask is made of the texts, so that the same badge
    is always the same bytes.

    Parameters:
        label: The text of the left side, such as the name of a step.
        value: The text of the right side, such as ``3/4``.
        color: The color of the right side, such as ``#fe7d37``.

    Returns:
        The SVG.

    Examples:
        >>> badge = svg("Triage", "3/4", "#fe7d37").decode()
        >>> "<title>Triage: 3/4</title>" in badge and 'role="img"' in badge
        True
        >>> svg("a", "b", "#4c1") == svg("a", "b", "#4c1")
        True
    """
    with IMPORT_GUARD:  # see import_guard.py
        import anybadge  # noqa: PLC0415 (only when a badge is drawn)

    drawn = anybadge.Badge(label, value, default_color=color)
    spoken = f"{label}: {value}"
    stable = "badge-" + hashlib.sha256(f"{spoken}\n{color}".encode()).hexdigest()[:12]
    text = drawn.badge_svg_text.replace(f'"{drawn.mask_str}"', f'"{stable}"').replace(
        f"#{drawn.mask_str})", f"#{stable})"
    )
    text = OWN_TITLE.sub("", text, count=1)
    return re.sub(
        r"<svg ([^>]*)>",
        lambda found: (
            f'<svg {OWN_NAME.sub("", found.group(1))} role="img" aria-label={quoteattr(spoken)}>'
            f"<title>{escape(spoken)}</title>"
        ),
        text,
        count=1,
    ).encode()


def png(label: str, value: str, color: str) -> bytes:
    """The same badge as a PNG, for places that show no SVG.

    Pillow draws it with its own font, so the server needs no fonts.

    Parameters:
        label: The text of the left side.
        value: The text of the right side.
        color: The color of the right side.

    Returns:
        The PNG.

    Examples:
        >>> png("Triage", "3/4", "#fe7d37")[1:4]
        b'PNG'
    """
    with IMPORT_GUARD:  # see import_guard.py
        from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415 (only for a PNG)

    font = ImageFont.load_default(size=FONT_SIZE * SCALE)
    widths = [font.getlength(text) + 2 * PADDING * SCALE for text in (label, value)]
    left, right = (round(width) for width in widths)
    image = Image.new("RGB", (left + right, HEIGHT * SCALE), LABEL_COLOR)
    draw = ImageDraw.Draw(image)
    draw.rectangle((left, 0, left + right, HEIGHT * SCALE), fill=color)
    middle = HEIGHT * SCALE / 2
    for text, start in ((label, 0), (value, left)):
        draw.text((start + PADDING * SCALE, middle), text, font=font, fill="#ffffff", anchor="lm")
    out = io.BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()
