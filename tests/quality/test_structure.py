"""The rules of AGENTS.md that can be checked."""

import ast
import re
from pathlib import Path

import pytest

from pycal_dashboard.github.permissions import EVENTS, REQUIRED

ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "pycal_dashboard"
MODULES = sorted(
    p for p in PACKAGE.rglob("*.py") if "migrations" not in p.parts and "errors" not in p.parts
)


@pytest.mark.parametrize("module", MODULES, ids=lambda p: str(p.relative_to(ROOT)))
def test_one_class_per_module(module):
    tree = ast.parse(module.read_text())
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) <= 1, classes


def test_no_inline_javascript_in_templates():
    """Small static scripts may enhance a page; no JavaScript is written into a template."""
    for template in (PACKAGE / "templates").rglob("*.html"):
        text = template.read_text()
        scripts = re.findall(r"<script[^>]*>", text)
        allowed = r'<script src="[^"]+" defer>|<script type="module" src="[^"]+">'  # modules defer
        assert all(re.fullmatch(allowed, s) for s in scripts), template
        assert "javascript:" not in text, template
        assert not re.search(r"\son[a-z]+=", text), template


def test_the_license_is_agpl():
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (ROOT / "LICENSE").read_text()


def test_permissions_are_documented():
    documented = (ROOT / "docs/reference/permissions.rst").read_text()
    for name, level in REQUIRED.items():
        assert f"``{name}``" in documented and level in documented
    for event in EVENTS:
        assert f"``{event}``" in documented


def test_todo_is_committed_with_checkboxes():
    text = (ROOT / "todo.txt").read_text()
    assert "- [x]" in text and "- [ ]" in text


def test_every_switch_is_the_partial():
    """Switches look and work the same everywhere: they all come from _switch.html."""
    for template in (PACKAGE / "templates").rglob("*.html"):
        if template.name == "_switch.html":
            continue
        assert 'class="switch"' not in template.read_text(), template
