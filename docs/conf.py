"""Sphinx configuration for the documentation of dashboard.pycal.org."""

import datetime
import os
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

html_baseurl = "https://dashboard-pycal-org.readthedocs.io/en/latest/"
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
