"""The links of the site into the documentation lead to the section they mean."""

import re
from pathlib import Path

import pytest
from django.test import RequestFactory

from pycal_dashboard.context import site

DOCS = Path(__file__).parent.parent.parent / "docs"
LABEL = re.compile(r"^\.\. _([\w-]+):\n\n(.+)\n([=\-~^]+)\n", re.MULTILINE)


def anchors() -> list[tuple[str, str, str]]:
    """The links of the site with an anchor: name, page and anchor."""
    links = site(RequestFactory().get("/"))["links"]
    found = []
    for name, url in links.items():
        if isinstance(url, str) and "#" in url and url.startswith(links["documentation"]):
            page, anchor = url.removeprefix(links["documentation"]).split("#")
            found.append((name, page, anchor))
    return found


def headings(page: str) -> dict[str, str]:
    """The labels of a page of the documentation with the heading right below each."""
    text = (DOCS / page.replace(".html", ".rst")).read_text()
    return {label: title for label, title, _line in LABEL.findall(text)}


@pytest.mark.django_db
@pytest.mark.parametrize(("name", "page", "anchor"), anchors())
def test_a_link_leads_to_its_heading(name, page, anchor):
    """The label is directly above a heading that has a word of the label."""
    found = headings(page)
    assert anchor in found, f"{name}: no label {anchor} right above a heading in {page}"
    words = set(anchor.split("-"))
    title = found[anchor].lower()
    assert any(word.rstrip("s") in title for word in words), (name, anchor, found[anchor])
