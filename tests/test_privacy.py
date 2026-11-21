"""The privacy policy says the truth: every model and field is in it, nothing else is loaded."""

import re
from pathlib import Path

import pytest
from django.apps import apps

from pycal_dashboard.models import Repository
from pycal_dashboard.privacy import COOKIES, DATA, EXTERNAL_HOSTS, MODELS, PARTIES
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate

ROOT = Path(__file__).parent.parent
# an element that makes the browser load something, with the host of another site
LOADED = re.compile(
    r"<(?:img|script|iframe|source|video|audio|embed|object)\b[^>]*?\b(?:src|data)="
    r'"(?:https?:)?//([^/"]+)'
    r'|<link\b[^>]*?\bhref="(?:https?:)?//([^/"]+)'
    r"|url\(\s*['\"]?(?:https?:)?//([^/'\")]+)"
    r"|@import\s+['\"](?:https?:)?//([^/'\"]+)",
    re.IGNORECASE,
)


def hosts_loaded(text: str) -> set[str]:
    """The hosts of other sites that a page, a style or a script loads from."""
    return {next(group for group in match if group) for match in LOADED.findall(text)}


def test_every_model_is_in_the_privacy_policy():
    """A new model or field fails here until the privacy policy says what it keeps."""
    models = {
        f"{model._meta.app_label}.{model.__name__}"
        for model in apps.get_app_config("pycal_dashboard").get_models()
    }
    listed = {name for name in MODELS if name.startswith("pycal_dashboard.")}
    assert listed == models
    for name, (entry, fields) in MODELS.items():
        model = apps.get_model(name)
        assert {f.name for f in model._meta.concrete_fields} == fields, name
        assert entry is None or entry in DATA, name


def test_every_entry_of_the_policy_describes_a_model():
    assert {entry for entry, _fields in MODELS.values() if entry} | {"requests"} == set(DATA)


def test_the_detector_finds_what_is_loaded():
    page = (
        '<img src="https://a.example/x.png"><script src="//b.example/s.js"></script>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=X">'
        '<a href="https://github.com/x">a link loads nothing</a>'
    )
    assert hosts_loaded(page) == {"a.example", "b.example", "fonts.googleapis.com"}
    assert hosts_loaded("@font-face { src: url('https://fonts.gstatic.com/x.woff2'); }") == {
        "fonts.gstatic.com"
    }
    assert hosts_loaded('@import "https://c.example/s.css";') == {"c.example"}


@pytest.mark.parametrize(
    "path",
    [
        *sorted((ROOT / "pycal_dashboard" / "templates").rglob("*.html")),
        *sorted((ROOT / "static").rglob("*.css")),
        *sorted((ROOT / "static").rglob("*.js")),
        ROOT / "docker" / "starting.html",
    ],
    ids=lambda path: str(path.relative_to(ROOT)),
)
def test_nothing_is_loaded_from_other_sites(path):
    """Such as Google Fonts: the files of the site load nothing from other sites."""
    assert hosts_loaded(path.read_text()) == set()


@pytest.mark.django_db
def test_the_pages_load_only_the_avatars_of_github(client, github, bob):
    github.add_repository("collective/icalendar", pulls=1)
    repository = Repository.objects.create(full_name="collective/icalendar")
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(repository)
    RepositoryUpdate(repository).run()
    client.force_login(bob)
    loaded = set()
    for path in (
        "/",
        "/about/",
        "/about/privacy/",
        "/licenses/",
        "/projects/",
        project.path(),
        project.path("pull-requests/"),
        project.path("collaborators/"),
        project.path("repositories/"),
        "/account/",
    ):
        answer = client.get(path)
        assert answer.status_code == 200, path
        loaded |= hosts_loaded(answer.content.decode())
    assert loaded == EXTERNAL_HOSTS == {"avatars.githubusercontent.com"}


@pytest.mark.django_db
def test_the_privacy_page_shows_the_policy(client, settings):
    settings.SITE_ADMINS = ["admin"]
    settings.EMAIL_HOST = "mail.example.org"
    page = client.get("/about/privacy/").content.decode()
    for key in DATA:
        assert f'data-kept="{key}"' in page
    for party in PARTIES:
        assert str(party["name"]) in page
    for name, _purpose in COOKIES:
        assert f"<code>{name}</code>" in page
    assert "<code>avatars.githubusercontent.com</code>" in page
    assert "The mail server of the site is mail.example.org." in page
    assert 'data-github-user="admin"' in page
    about = client.get("/about/").content.decode()
    assert 'href="/about/privacy/"' in about.split('<ul class="tabs">')[1]


@pytest.mark.django_db
def test_without_a_mail_server_the_policy_says_so(client, settings):
    settings.EMAIL_HOST = ""
    assert "The site sends no emails" in client.get("/about/privacy/").content.decode()


@pytest.mark.django_db
def test_the_about_pages_have_tabs(client):
    for path, current in [
        ("/about/", "Contact"),
        ("/about/privacy/", "Privacy"),
        ("/licenses/", "Licenses"),
        ("/about/version/", "Version"),
        ("/about/github-app/", "GitHub App"),
    ]:
        tabs = client.get(path).content.decode().split('<ul class="tabs">')[1].split("</ul>")[0]
        assert re.search(rf'aria-current="page">{current}<', tabs), path
