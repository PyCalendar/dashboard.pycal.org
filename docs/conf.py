"""Sphinx configuration for the documentation of dashboard.pycal.org."""

import datetime
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))  # pycal_dashboard.errors for autodoc
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pycal_dashboard.settings")
os.environ.setdefault("SECRET_KEY", "documentation")
os.environ.setdefault("DATA_DIR", str(ROOT / "docs" / "_build" / "data"))
import django  # noqa: E402
from sphinx.application import Sphinx  # noqa: E402

django.setup()

project = "dashboard.pycal.org"
copyright = f"{datetime.date.today().year}, dashboard.pycal.org contributors"  # noqa: A001
author = "dashboard.pycal.org contributors"

extensions = [
    "notfound.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",  # the docstrings in the style of Google, such as of the conditions
    "sphinx_copybutton",
    "sphinx_design",
]

html_baseurl = "https://docs.dashboard.pycal.org/"
html_theme = "pydata_sphinx_theme"
html_favicon = "../static/img/favicon.png"
html_logo = "../static/img/favicon.png"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/PyCalendar/dashboard.pycal.org",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
        {
            "name": "dashboard.pycal.org",
            "url": "https://dashboard.pycal.org/",
            "icon": "fa-solid fa-gauge",
            "type": "fontawesome",
        },
    ],
    "logo": {"text": "dashboard.pycal.org"},
    "show_toc_level": 2,
    "navigation_with_keys": True,
}
html_context = {
    "github_user": "PyCalendar",
    "github_repo": "dashboard.pycal.org",
    "github_version": "main",
    "doc_path": "docs",
}
html_static_path = ["_static"]
html_css_files = ["style.css"]

autodoc_member_order = "bysource"
autodoc_typehints = "none"  # the signatures name the models, which have no pages here
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
exclude_patterns = ["_build"]
linkcheck_ignore = [r"http://localhost", r"https://dashboard\.pycal\.org.*"]


def unreleased_changes(root: Path = ROOT) -> str:
    """The changes since the last release, drafted by towncrier from the fragments in ``news/``.

    Parameters:
        root: The project, with ``pyproject.toml`` and ``news/``.

    Returns:
        The section of the changelog, "" without fragments.

    Examples:
        >>> text = unreleased_changes()  # none right after a release
        >>> text == "" or text.startswith("Unreleased")
        True
    """
    if not any(not path.name.startswith(".") for path in (root / "news").iterdir()):
        return ""
    draft = subprocess.run(
        [sys.executable, "-m", "towncrier", "build", "--draft", "--version", "unreleased"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    # the version comes from the git tag of the release: the title says that it is not released
    body = draft.split("\n", 2)[2]
    return f"Unreleased\n----------\n{body}"


def write_unreleased_changes(path: Path = ROOT / "docs" / "_build" / "unreleased.rst") -> None:
    """Write the changes since the last release for ``changelog.rst``, which includes them.

    The file is written only when it changes, so that ``make livehtml`` does not build again
    and again.

    Parameters:
        path: The file.
    """
    text = unreleased_changes()
    if not path.is_file() or path.read_text() != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


write_unreleased_changes()


# the sections of the docstring of an error after why it appears, in their order, with their
# headings in the documentation; "Note:" becomes a note (napoleon makes it ".. note::")
ERROR_SECTIONS = {"Resolve:": "How to resolve it:", "Context:": "Context:"}


def error_facts(
    app: Sphinx, what: str, name: str, obj: object, options: dict, lines: list[str]
) -> None:
    """Show the title and HTTP status of each error, why it appears and how to resolve it.

    The docstring of an error has, in this order: one sentence why it appears, maybe followed
    by the cases that lead to it; ``Resolve:`` with the actions alone; ``Context:`` (optional)
    that explains it; ``Note:`` (optional) with what fits nowhere else. See
    ``tests/test_errors.py``.

    Parameters:
        app: Sphinx.
        what: The kind of object, such as ``exception``.
        name: The full name.
        obj: The object.
        options: Of autodoc.
        lines: The lines of the docstring, changed in place.
    """
    import textwrap

    from pycal_dashboard.errors import DashboardError

    if what not in ("class", "exception") or not isinstance(obj, type):
        return
    if not issubclass(obj, DashboardError) or not lines:
        return
    parts: dict[str, list[str]] = {"why": []}
    part = "why"
    for line in lines:
        if line in ERROR_SECTIONS or line.startswith(".. note::") or line == "Note:":
            part = line
            parts[part] = [line] if part not in ERROR_SECTIONS else []
            continue
        parts[part].append(line)
    result = [f"**{obj.title}** · HTTP {obj.status}", "", "**Why it appears:**", "", *parts["why"]]
    for section, heading in ERROR_SECTIONS.items():
        if section in parts:
            body = textwrap.dedent("\n".join(parts[section])).strip("\n").splitlines()
            result += ["", f"**{heading}**", "", *body]
    for section, body in parts.items():
        if section not in ERROR_SECTIONS and section != "why":
            result += ["", *body]
    lines[:] = result


def setup(app: Sphinx) -> None:
    """Connect the error facts.

    Parameters:
        app: Sphinx.
    """
    app.connect("autodoc-process-docstring", error_facts)
