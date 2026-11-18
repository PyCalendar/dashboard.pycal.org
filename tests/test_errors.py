"""Every error is documented: why it appears and how to resolve it, with a working link."""

import re
from pathlib import Path

import pytest

from pycal_dashboard import errors
from pycal_dashboard.errors import DashboardError, all_errors, translate

DOCS = Path(__file__).parents[1] / "docs"
ERRORS = sorted(all_errors().values(), key=lambda cls: cls.__name__)


@pytest.mark.parametrize("cls", ERRORS, ids=lambda cls: cls.__name__)
def test_error_has_title_and_explanation(cls):
    assert cls.title and cls.title[0].isupper()
    doc = (cls.__doc__ or "").strip()
    summary, _, explanation = doc.partition("\n\n")
    assert summary.endswith("."), "the first line says why the error appears"
    assert explanation.strip(), "the rest says how to resolve it"
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
