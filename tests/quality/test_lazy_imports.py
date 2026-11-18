"""Every lazy import goes through the import guard, so that threads cannot stop each other.

The site imports some packages inside functions, when they are first needed, which keeps its
memory low when idle. Threads that serve pages at the same time could otherwise import them at
the same time in another order, which Python's import can stop as a deadlock.
"""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "pycal_dashboard"


def unguarded_imports(source: str) -> list[int]:
    """The lines of the imports inside functions that are not inside ``with IMPORT_GUARD:``.

    Args:
        source: The code of a module.

    Returns:
        The line numbers.

    Examples:
        >>> unguarded_imports("import os\\ndef f():\\n    import json\\n")
        [3]
        >>> unguarded_imports("def f():\\n    with IMPORT_GUARD:\\n        import json\\n")
        []
    """
    found = []

    def walk(node: ast.AST, in_function: bool, guarded: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)) and in_function and not guarded:
                found.append(child.lineno)
            walk(
                child,
                in_function or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)),
                guarded
                or (
                    isinstance(child, ast.With)
                    and any(
                        ast.unparse(item.context_expr) == "IMPORT_GUARD" for item in child.items
                    )
                ),
            )

    walk(ast.parse(source), False, False)
    return found


def test_the_check_finds_an_unguarded_import():
    """The check itself: an import in a function, in a method and in a nested block."""
    source = "class A:\n    def f(self):\n        if True:\n            from x import y\n"
    assert unguarded_imports(source) == [4]
    assert unguarded_imports("def f():\n    with open('x'):\n        import json\n") == [3]


def test_every_lazy_import_goes_through_the_guard():
    """Each import inside a function of the site is inside ``with IMPORT_GUARD:``."""
    found = [
        f"{path.relative_to(ROOT)}:{line}"
        for path in sorted(PACKAGE.rglob("*.py"))
        if "migrations" not in path.parts
        for line in unguarded_imports(path.read_text())
    ]
    assert found == [], "import inside ``with IMPORT_GUARD:`` (pycal_dashboard/import_guard.py)"


IMPORT_AT_ONCE = """
import importlib.abc, json, os, sys, threading
import django
django.setup()
from pycal_dashboard.import_guard import IMPORT_GUARD

WATCHED = {"httpx", "jwt", "cryptography", "reuse", "piplicenses"}
held = {}

class Watch(importlib.abc.MetaPathFinder):
    # records whether the thread that imports a watched package holds the guard
    def find_spec(self, name, path, target=None):
        if name in WATCHED:
            held.setdefault(name, IMPORT_GUARD._is_owned())
        return None

sys.meta_path.insert(0, Watch())
assert not WATCHED & set(sys.modules), "already imported: " + str(WATCHED & set(sys.modules))

from pycal_dashboard import licenses
from pycal_dashboard.github.app_check import AppCheck
from pycal_dashboard.github.client import GitHubClient

WORK = [
    lambda: GitHubClient("token").http.close(),
    lambda: AppCheck.token(),
    lambda: licenses.read_reused(),
    lambda: licenses.read_installed(),
]
errors = []
start = threading.Barrier(8)

def work(n):
    start.wait()
    try:
        WORK[n % len(WORK)]()
    except Exception as error:
        errors.append(repr(error))

threads = [threading.Thread(target=work, args=(n,), daemon=True) for n in range(8)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join(60)
print(json.dumps({
    "stuck": sum(thread.is_alive() for thread in threads),
    "errors": errors,
    "held": held,
}))
"""


def test_threads_import_the_heavy_packages_at_the_same_time(tmp_path, private_key):
    """In a fresh process, eight threads need the heavy packages at once: none waits forever,
    and each package is imported while its thread holds the import guard."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GITHUB_", "DJANGO_", "DATABASE_"))
    }
    environment.update(
        DJANGO_SETTINGS_MODULE="pycal_dashboard.settings",
        DATA_DIR=str(tmp_path),
        SECRET_KEY="test",
        GITHUB_APP_ID="1",
        GITHUB_APP_PRIVATE_KEY=private_key,
    )
    result = subprocess.run(
        [sys.executable, "-c", IMPORT_AT_ONCE],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    done = json.loads(result.stdout.strip().splitlines()[-1])
    assert done["stuck"] == 0 and done["errors"] == []
    assert done["held"] == dict.fromkeys(
        ["cryptography", "httpx", "jwt", "piplicenses", "reuse"], True
    )
