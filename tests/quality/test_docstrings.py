"""The docstrings name every argument under "Parameters:", never "Args:"; every argument is typed.

Ruff checks the types (ANN001, ANN002, ANN003) and the style of Google; its check of the
arguments (D417) knows only "Args:", so this test checks "Parameters:".
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[2] / "pycal_dashboard"
MODULES = sorted(p for p in PACKAGE.rglob("*.py") if "migrations" not in p.parts)


def arguments(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """The names of the arguments a docstring describes: without self and cls."""
    found = [a.arg for a in [*function.args.posonlyargs, *function.args.args]]
    found += [a.arg for a in function.args.kwonlyargs]
    if function.args.vararg:
        found.append("*" + function.args.vararg.arg)
    if function.args.kwarg:
        found.append("**" + function.args.kwarg.arg)
    return [name for name in found if name not in ("self", "cls")]


def described(docstring: str) -> set[str]:
    """The names under "Parameters:" of a docstring."""
    names = set()
    inside = False
    indent = None
    for line in docstring.splitlines():
        if line.strip() == "Parameters:":
            inside, indent = True, None
            continue
        if inside:
            if not line.strip():
                continue
            width = len(line) - len(line.lstrip())
            if indent is None:
                indent = width
            if width < indent:
                inside = False
                continue
            if width == indent and ":" in line:
                names.add(line.strip().split(":")[0].split(" (")[0])
    return names


@pytest.mark.parametrize("path", MODULES, ids=lambda p: str(p.relative_to(PACKAGE)))
def test_every_argument_is_under_parameters(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        docstring = ast.get_docstring(node) or ""
        assert "Args:" not in docstring.split(), f"{path.name}:{node.lineno} uses Args:"
        names = arguments(node)
        if not docstring or not names:
            continue
        missing = [name for name in names if name not in described(docstring)]
        assert not missing, f"{path.name}:{node.lineno} {node.name}: {missing} not in Parameters:"


def test_the_check_finds_a_missing_argument():
    function = ast.parse(
        'def f(a: int, b: int):\n    """Add.\n\n    Parameters:\n        a: One.\n    """\n'
    ).body[0]
    assert arguments(function) == ["a", "b"]
    assert described(ast.get_docstring(function)) == {"a"}
