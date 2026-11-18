"""The settings: organizations, the client for signing in and the documentation of each."""

import re
from pathlib import Path

import pytest

from pycal_dashboard.errors import InvalidOrganizationSetting
from pycal_dashboard.organizations import parse_organizations

ROOT = Path(__file__).parents[1]


def test_invalid_organization():
    with pytest.raises(InvalidOrganizationSetting):
        parse_organizations("PyCalendar, not valid")


def test_every_setting_is_documented():
    names = set(
        re.findall(
            r'env(?:\.\w+)?\(\s*"([A-Z_]+)"', (ROOT / "pycal_dashboard/settings.py").read_text()
        )
    )
    names |= {
        "COLOR_<NAME>",
        "GITHUB_CLIENT_ID",
        "GITHUB_SECRET",
        "GITHUB_OAUTH_CLIENT_ID",
        "GITHUB_OAUTH_SECRET",
    }
    documented = (ROOT / "docs/reference/settings.rst").read_text()
    missing = [name for name in sorted(names) if f"``{name}``" not in documented]
    assert not missing


def test_every_setting_is_in_the_example():
    """.env.example lists every variable of the documentation, and nothing else."""
    example = (ROOT / ".env.example").read_text()
    in_example = set(re.findall(r"^#? ?([A-Z][A-Z_]+)=", example, re.MULTILINE))
    # the terms of the definition lists: the lines that start with a name
    terms = re.findall(r"^``.*$", (ROOT / "docs/reference/settings.rst").read_text(), re.MULTILINE)
    documented = {name for line in terms for name in re.findall(r"``([A-Z][A-Z_]+)``", line)}
    colors = {name for name in in_example if name.startswith("COLOR_")}
    assert sorted(documented - in_example) == []
    assert sorted(in_example - documented - colors) == []


def test_every_color_is_in_the_example():
    from pycal_dashboard.theme import DARK, LIGHT

    example = (ROOT / ".env.example").read_text()
    for name, value in LIGHT.items():
        assert f"# COLOR_{name.upper()}={value}\n" in example
    for name, value in DARK.items():
        assert f"# COLOR_DARK_{name.upper()}={value}\n" in example


def test_every_variable_of_the_code_is_documented():
    """Also those of the container and of the libraries, such as PORT."""
    code = "\n".join(
        path.read_text()
        for pattern in ("pycal_dashboard/**/*.py", "docker/*.sh", "Dockerfile")
        for path in ROOT.glob(pattern)
    )
    names = set(re.findall(r'env(?:\.\w+)?\(\s*"([A-Z_]+)"', code))
    names |= set(re.findall(r"\$\{?(PORT|WORKERS|THREADS)\b", code))
    documented = (ROOT / "docs/reference/settings.rst").read_text()
    assert [name for name in sorted(names) if f"``{name}``" not in documented] == []


@pytest.mark.parametrize("name", [".env.example", ".env.development.example"])
def test_every_setting_of_the_example_is_described(name):
    """Each setting has its description: a line with ## directly above it."""
    lines = (ROOT / name).read_text().splitlines()
    for number, line in enumerate(lines):
        if re.match(r"^#? ?[A-Z][A-Z_]+=", line):
            assert lines[number - 1].startswith("## "), line
