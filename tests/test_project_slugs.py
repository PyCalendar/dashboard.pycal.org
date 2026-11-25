"""The addresses of projects: random by default, chosen, suggested, renamed without broken links."""

import re

import pytest
from django.core.exceptions import ValidationError

from pycal_dashboard.errors import ProjectSlugTaken
from pycal_dashboard.models import Project, ProjectSlug, Repository
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.project_editor import ProjectEditor

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(bob):
    return ProjectEditor.create(bob, "iCalendar")


def editor(project):
    return ProjectEditor(ProjectAccess(project, project.created_by))


def test_a_project_made_outside_the_site_gets_a_random_slug(db):
    project = Project.objects.create(name="From the admin")
    assert re.fullmatch("[0-9a-f]{6}", project.slug)
    assert list(project.slugs.values_list("slug", flat=True)) == [project.slug]
    assert project.path() == f"/projects/{project.slug}/"


def test_choose_the_slug_when_creating(client, bob):
    client.force_login(bob)
    client.post("/projects/new/", {"name": "Mine", "slug": " PyCal~iCalendar "})
    project = Project.objects.get()
    assert project.slug == "pycal~icalendar"
    assert client.get("/projects/new/").content.decode().count('name="slug"') == 1


@pytest.mark.parametrize(
    ("slug", "error"),
    [
        ("a_b", "Not an address of a project"),
        ("a--b", "Not an address of a project"),
        ("-a", "Not an address of a project"),
        ("a~b~c", "Not an address of a project"),
        ("ö", "Not an address of a project"),
        ("x" * 81, "Not an address of a project"),
        ("new", "Not an address of a project"),
    ],
)
def test_the_slug_has_the_letters_of_a_github_handle(client, bob, slug, error):
    client.force_login(bob)
    page = client.post("/projects/new/", {"name": "Mine", "slug": slug})
    assert page.status_code == 400 and error in page.content.decode()
    assert not Project.objects.exists()


def test_a_slug_is_unique(client, bob, project):
    editor(project).rename("taken")
    client.force_login(bob)
    page = client.post("/projects/new/", {"name": "Mine", "slug": "Taken"})
    assert "The address is taken" in page.content.decode()


def test_the_address_is_the_slug_only(client, project):
    """The name after the slug, in the addresses before, leads to the same page without it."""
    assert project.path() == f"/projects/{project.slug}/"
    assert client.get(f"/projects/{project.slug}/").status_code == 200
    for old, new in [
        ("anything/", ""),
        ("anything/settings/?a=1", "settings/?a=1"),
        ("anything/repositories/", "settings/repositories/"),
        ("anything/people/", "settings/collaborators/"),
        ("repositories/?a=1", "settings/repositories/?a=1"),  # before they were in the settings
        ("collaborators/", "settings/collaborators/"),
    ]:
        answer = client.get(f"/projects/{project.slug}/{old}")
        assert answer.status_code == 301, old
        assert answer["Location"] == project.path(new), old
    assert client.get(f"/projects/{project.slug}/anything/nothing/").status_code == 404
    assert client.get(f"/projects/{project.slug}.json").json()["name"] == "iCalendar"


def test_rename_and_the_old_links_keep_working(client, bob, project):
    old = project.slug
    client.force_login(bob)
    page = client.post(
        f"/projects/{old}/address/", {"slug": "ical", "back": "settings/"}, follow=True
    ).content.decode()
    assert "The address of the project is /projects/ical/ now" in page
    project.refresh_from_db()
    assert project.slug == "ical"
    for path, target in [
        (f"/projects/{old}/", "/projects/ical/"),
        (f"/projects/{old}/collaborators/?a=1", "/projects/ical/settings/collaborators/?a=1"),
        (f"/projects/{old.upper()}/settings/", "/projects/ical/settings/"),
        (f"/projects/{old}/", "/projects/ical/"),
    ]:
        answer = client.get(path)
        assert (answer.status_code, answer["Location"]) == (301, target), path
    history = {s.slug: s.until for s in ProjectSlug.objects.filter(project=project)}
    assert history["ical"] is None and history[old] is not None
    assert "data-old-slugs" in client.get(project.path("settings/")).content.decode()


def test_old_slugs_are_never_used_again(bob, project):
    old = project.slug
    editor(project).rename("ical")
    other = ProjectEditor.create(bob, "Other")
    with pytest.raises(ProjectSlugTaken):
        editor(other).rename(old)
    project.delete()
    with pytest.raises(ProjectSlugTaken):
        editor(other).rename("ical")  # also after the project is deleted
    assert ProjectSlug.objects.filter(slug="ical", project=None).exists()


def test_a_project_may_go_back_to_its_old_slug(project):
    old = project.slug
    editor(project).rename("ical")
    assert editor(project).rename(old)
    assert ProjectSlug.objects.get(slug=old).until is None
    assert ProjectSlug.objects.get(slug="ical").until is not None
    assert not editor(project).rename(old.upper())  # the same slug


def test_only_owners_change_the_address(client, project, alice):
    editor(project).share("alice", "write")
    client.force_login(alice)
    answer = client.post(f"/projects/{project.slug}/address/", {"slug": "mine"})
    assert answer.status_code == 403 and "Only the owners" in answer.content.decode()
    assert 'id="address"' not in client.get(project.path("settings/")).content.decode()


def test_an_old_slug_of_a_private_project_reveals_nothing(client, bob):
    project = ProjectEditor.create(bob, "Secret", public=False)
    old = project.slug
    editor(project).rename("secret")
    assert client.get(f"/projects/{old}/").status_code == 404


def test_the_suggestion_after_the_one_repository(client, bob, project):
    assert editor(project).suggestion() is None  # no repository
    project.repositories.add(Repository.objects.create(full_name="collective/icalendar"))
    assert editor(project).suggestion() == "icalendar"
    other = ProjectEditor.create(bob, "Other", slug="icalendar")
    assert editor(project).suggestion() == "collective~icalendar"
    editor(other).rename("collective~icalendar")  # icalendar stays taken: it was the old one
    assert editor(project).suggestion() == "collective~icalendar-2"
    editor(project).rename("collective~icalendar-2")
    assert editor(project).suggestion() is None  # it has it
    project.repositories.add(Repository.objects.create(full_name="collective/x"))
    assert editor(project).suggestion() is None  # more repositories: the slug stays


def test_use_the_suggestion_from_the_repositories(client, bob, project):
    project.repositories.add(Repository.objects.create(full_name="collective/icalendar"))
    client.force_login(bob)
    page = client.get(project.path("settings/repositories/")).content.decode()
    assert "data-suggestion" in page and "<code>icalendar</code>" in page
    answer = client.post(
        f"/projects/{project.slug}/address/",
        {"slug": "icalendar", "back": "settings/repositories/"},
    )
    assert answer["Location"] == "/projects/icalendar/settings/repositories/"
    answer = client.post("/projects/icalendar/address/", {"slug": "a", "back": "/elsewhere"})
    assert answer["Location"] == "/projects/a/settings/"


def test_the_admin_checks_the_slug(project):
    project.slug = "Bad Slug"
    with pytest.raises(ValidationError):
        project.clean()
    other = Project.objects.create(name="Other")
    other.slug = project.slugs.first().slug
    with pytest.raises(ValidationError):
        other.clean()
    other.slug = "Fine~One"
    other.clean()
    assert other.slug == "fine~one"
