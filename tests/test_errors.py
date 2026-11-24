"""Every error is documented: why it appears and how to resolve it, with a working link."""

import inspect
import re
from pathlib import Path

import pytest

from pycal_dashboard import errors
from pycal_dashboard.errors import DashboardError, all_errors, translate

DOCS = Path(__file__).parents[1] / "docs"
ERRORS = sorted(all_errors().values(), key=lambda cls: cls.__name__)


SECTIONS = ("Resolve:", "Context:", "Note:")  # in this order; Context and Note may be missing


def sections(cls: type) -> dict[str, str]:
    """The parts of the docstring of an error: ``why``, then its sections, by their heading."""
    parts = {"why": []}
    part = "why"
    for line in inspect.cleandoc(cls.__doc__ or "").splitlines():
        if line in SECTIONS:
            assert line not in parts, f"{line} twice"
            part = line
            parts[part] = []
        else:
            assert part == "why" or not line or line.startswith("    "), f"{part} is indented"
            parts[part].append(line)
    return {part: "\n".join(lines).strip() for part, lines in parts.items()}


@pytest.mark.parametrize("cls", ERRORS, ids=lambda cls: cls.__name__)
def test_error_has_title_and_explanation(cls):
    """Why it appears, in one sentence, maybe with its cases; the actions that resolve it; its
    context; a note with the rest (docs/reference/errors.rst)."""
    assert cls.title and cls.title[0].isupper()
    parts = sections(cls)
    summary = parts["why"].split("\n\n")[0]
    assert summary.endswith("."), "the first sentence says why the error appears"
    assert not re.search(r"[.!?] +[A-Z]", " ".join(summary.split())), "one sentence"
    assert parts.get("Resolve:"), "Resolve: says what to do"
    assert list(parts)[1:] == [s for s in SECTIONS if s in parts], "in the order of SECTIONS"
    assert cls.__doc__ != DashboardError.__doc__ or cls is DashboardError
    assert 100 <= cls.status < 600


@pytest.mark.parametrize("cls", ERRORS, ids=lambda cls: cls.__name__)
def test_error_is_exported_and_documented(cls):
    assert getattr(errors, cls.__name__) is cls
    reference = (DOCS / "reference" / "errors.rst").read_text()
    assert f".. automodule:: {cls.__module__}\n" in reference
    assert cls.docs_url().endswith(f"#{cls.__module__}.{cls.__name__}")


@pytest.mark.parametrize("cls", ERRORS, ids=lambda cls: cls.__name__)
def test_guide_exists(cls):
    if cls.guide:
        page = cls.guide.split("#")[0].replace(".html", ".rst")
        assert (DOCS / page).is_file(), cls.guide


def test_translate():
    import httpx

    assert translate(httpx.ConnectError("x")).code == "GitHubUnreachable"
    assert translate(httpx.HTTPError("x")).code == "GitHubError"
    error = errors.InvalidInstallationId("installation_id='x'")
    assert translate(error) is error
    assert error.as_json()["title"] == "Invalid installation"


def test_one_class_per_cause():
    titles = [cls.title for cls in ERRORS]
    assert len(titles) == len(set(titles)), [t for t in titles if titles.count(t) > 1]


def test_docstrings_reference_existing_pages():
    for cls in ERRORS:
        for page in re.findall(r":doc:`([^`]+)`", cls.__doc__ or ""):
            assert (DOCS / f"{page.lstrip('/')}.rst").is_file(), (cls, page)
