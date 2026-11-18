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
    example = (ROOT / ".env.example").read_text()
    for name in (
        "SITE_URL",
        "ALLOWED_HOSTS",
        "GITHUB_ORGANIZATIONS",
        "SITE_ADMINS",
    ):
        assert name in example
