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

django.setup()

project = "dashboard.pycal.org"
copyright = f"{datetime.date.today().year}, dashboard.pycal.org contributors"  # noqa: A001
author = "dashboard.pycal.org contributors"

extensions = [
    "notfound.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
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
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
exclude_patterns = ["_build"]
linkcheck_ignore = [r"http://localhost", r"https://dashboard\.pycal\.org.*"]


def unreleased_changes(root: Path = ROOT) -> str:
    """The changes since the last release, drafted by towncrier from the fragments in ``news/``.

    Args:
        root: The project, with ``pyproject.toml`` and ``news/``.

    Returns:
        The section of the changelog, "" without fragments.

    Examples:
        >>> unreleased_changes().startswith("Unreleased")
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

    Args:
        path: The file.
    """
    text = unreleased_changes()
    if not path.is_file() or path.read_text() != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


write_unreleased_changes()


def error_facts(app, what, name, obj, options, lines):
    """Show the title and HTTP status of each error, why it appears and how to resolve it.

    The first paragraph of the docstring of an error says why it appears, the rest how to
    resolve it.

    Args:
        app: Sphinx.
        what: The kind of object, such as ``exception``.
        name: The full name.
        obj: The object.
        options: Of autodoc.
        lines: The lines of the docstring, changed in place.
    """
    from pycal_dashboard.errors import DashboardError

    if what not in ("class", "exception") or not isinstance(obj, type):
        return
    if not issubclass(obj, DashboardError) or not lines:
        return
    split = lines.index("") if "" in lines else len(lines)
    why, how = lines[:split], [line for line in lines[split + 1 :]]
    lines[:] = [f"**{obj.title}** · HTTP {obj.status}", "", "**Why it appears:**", *why]
    if any(line.strip() for line in how):
        lines += ["", "**How to resolve it:**", *how]


def setup(app):
    """Connect the error facts.

    Args:
        app: Sphinx.
    """
    app.connect("autodoc-process-docstring", error_facts)
