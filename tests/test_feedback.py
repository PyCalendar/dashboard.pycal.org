"""The form of GitHub for problems and feedback, and the links of the pages to it."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "feedback.yml"


def test_the_form_asks_for_what_helps_and_says_where_to_find_it():
    form = yaml.safe_load(FORM.read_text())
    assert form["name"] and form["description"]
    fields = {item["id"]: item for item in form["body"] if "id" in item}
    assert {"kind", "problem", "steps", "page", "error", "version", "screenshots"} <= set(fields)
    assert fields["problem"]["validations"]["required"] is True
    for name in ("error", "version", "screenshots", "page"):
        assert fields[name]["attributes"]["description"], name  # where to find it
    assert "Details to copy" in fields["error"]["attributes"]["description"]
    assert "/about/version/" in fields["version"]["attributes"]["description"]


@pytest.mark.django_db
def test_the_pages_link_the_form(client):
    page = client.get("/about/").content.decode()
    assert "/issues/new?template=feedback.yml" in page
    guide = (ROOT / "docs" / "how-to" / "report-bug.rst").read_text()
    assert "issues/new?template=feedback.yml" in guide and "Details to copy" in guide
