"""The documentation shows the changes since the last release: towncrier drafts them from news/."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def conf():
    """The configuration of Sphinx, docs/conf.py, as a module."""
    spec = importlib.util.spec_from_file_location("docs_conf", ROOT / "docs" / "conf.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_changelog_includes_every_news_fragment():
    """Each fragment of news/ is in the section Unreleased of the changelog; right after a
    release there are none, and no section."""
    text = " ".join(conf().unreleased_changes().split())
    fragments = [path for path in (ROOT / "news").iterdir() if not path.name.startswith(".")]
    if not fragments:
        assert text == ""
        return
    assert text.startswith("Unreleased ---------- ")
    for path in fragments:
        assert " ".join(path.read_text().split()) in text, path.name


def test_the_changelog_includes_the_draft_above_the_releases():
    """towncrier build writes each release below the start string, the draft stays on top."""
    changelog = (ROOT / "docs" / "changelog.rst").read_text()
    assert changelog.index(".. include:: _build/unreleased.rst") < changelog.index(
        ".. towncrier release notes start"
    )


def test_news_fragments_have_no_ending():
    """Fragments are named like 12.feature or +topic.bugfix, without .rst."""
    assert [path.name for path in (ROOT / "news").glob("*.rst")] == []


def test_a_draft_of_the_fragments(tmp_path):
    """With fragments in news/, the section Unreleased has them."""
    import shutil

    for name in ("pyproject.toml",):
        shutil.copy(ROOT / name, tmp_path / name)
    (tmp_path / "news").mkdir()
    (tmp_path / "docs").mkdir()
    shutil.copy(ROOT / "docs" / "changelog.rst", tmp_path / "docs" / "changelog.rst")
    (tmp_path / "news" / "+topic.feature").write_text("Something new.\n")
    text = " ".join(conf().unreleased_changes(tmp_path).split())
    assert text.startswith("Unreleased ---------- ") and "Something new." in text
