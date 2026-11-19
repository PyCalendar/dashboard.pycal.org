"""Notifications on the site: an installation that needs permissions, read, resolved, renewed."""

import pytest

from pycal_dashboard.models import Installation, Notification, Repository
from pycal_dashboard.services.permission_notice import PermissionNotice
from pycal_dashboard.services.project_access import ProjectAccess
from pycal_dashboard.services.project_editor import ProjectEditor

pytestmark = pytest.mark.django_db
LACKING = {"metadata": "read", "issues": "read"}


@pytest.fixture
def installation(bob, alice):
    """An installation that lacks permissions, on a repository of a project of bob and alice."""
    installation = Installation.objects.create(
        github_id=11,
        account_login="collective",
        account_type="Organization",
        permissions=LACKING,
        admin_github_ids=["42"],  # alice installed it
    )
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(
        Repository.objects.create(full_name="collective/icalendar", installation=installation)
    )
    return installation


def test_the_people_of_an_installation_are_notified(installation, bob, alice):
    PermissionNotice(installation).send_if_needed()
    notified = Notification.objects.order_by("user__username")
    assert [n.user.username for n in notified] == ["alice", "bob"]
    first = notified[0]
    assert first.params["account"] == "collective" and "pull_requests" in first.params["missing"]
    assert first.url == installation.settings_url and first.read is None


def test_also_without_emails(installation, bob):
    from pycal_dashboard.models import Preferences

    Preferences.objects.create(user=bob, email_permissions=False)
    PermissionNotice(installation).send_if_needed()
    assert Notification.objects.filter(user=bob).exists()


def test_the_menu_counts_them_and_the_page_shows_them(client, installation, bob):
    PermissionNotice(installation).send_if_needed()
    client.force_login(bob)
    page = client.get("/projects/").content.decode()
    assert 'data-notification-count title="1 unread notification">1</span>' in page
    page = client.get("/account/notifications/").content.decode()
    item = page.split('data-notification="permissions"')[1].split("notification-meta")[0]
    # the title, the button with the documentation, the list of permissions, the rest
    title, button, listed, text = (
        item.index("notification-title"),
        item.index("Accept the permissions on GitHub"),
        item.index("data-permission-list"),
        item.index("An owner of the account opens"),
    )
    assert title < button < listed < text
    assert "The GitHub App needs more permissions on collective" in item
    # as the settings of the app on GitHub name them
    assert "<strong>Repository permissions</strong>" in item
    assert '<span class="permission-name">Pull requests</span>: Read and write' in item
    assert installation.settings_url in item and "Mark as read" in page


def test_mark_as_read(client, installation, bob):
    PermissionNotice(installation).send_if_needed()
    client.force_login(bob)
    notification = Notification.objects.get(user=bob)
    client.post("/account/notifications/", {"read": notification.pk})
    notification.refresh_from_db()
    assert notification.read is not None
    assert "data-notification-count" not in client.get("/projects/").content.decode()
    assert "data-notifications" in client.get("/account/notifications/").content.decode()


def test_mark_all_as_read_only_of_oneself(client, installation, bob, alice):
    PermissionNotice(installation).send_if_needed()
    client.force_login(bob)
    client.post("/account/notifications/", {"read": "all"})
    assert Notification.objects.get(user=bob).read is not None
    assert Notification.objects.get(user=alice).read is None
    other = Notification.objects.get(user=alice)
    client.post("/account/notifications/", {"read": other.pk})  # not bob's
    other.refresh_from_db()
    assert other.read is None


def test_accepted_permissions_resolve_it(client, installation, bob):
    from pycal_dashboard.github.permissions import REQUIRED

    PermissionNotice(installation).send_if_needed()
    installation.permissions = dict(REQUIRED)
    installation.save()
    PermissionNotice(installation).send_if_needed()
    assert Notification.objects.get(user=bob).resolved is not None
    client.force_login(bob)
    page = client.get("/account/notifications/").content.decode()
    assert "data-no-notifications" in page and "data-resolved" in page


def test_other_missing_permissions_make_it_unread_again(installation, bob):
    PermissionNotice(installation).send_if_needed()
    Notification.objects.update(read="2026-11-19T10:00:00Z")
    PermissionNotice(installation).send_if_needed()  # the same: stays read
    assert Notification.objects.get(user=bob).read is not None
    installation.permissions = {"metadata": "read"}
    installation.save()
    PermissionNotice(installation).send_if_needed()
    assert Notification.objects.get(user=bob).read is None


def test_a_writer_of_a_project_is_notified_too(installation, bob):
    from tests.conftest import person

    carol = person(44, "carol")
    project = installation.repositories.get().projects.get()
    ProjectEditor(ProjectAccess(project, bob)).share("carol", "write")
    PermissionNotice(installation).send_if_needed()
    assert Notification.objects.filter(user=carol).exists()


def test_visitors_have_no_notifications(client, db):
    assert client.get("/account/notifications/").status_code == 302


def test_the_administrators_are_told_when_the_app_lacks_something(github, settings, db):
    """At the start of the site: the app first, whose owners add what it lacks."""
    from django.core.management import call_command

    from tests.conftest import person

    settings.SITE_ADMINS = ["admin"]
    admin = person(7, "admin")
    github.app["permissions"] = {"metadata": "read"}
    github.app["events"] = ["issues"]
    call_command("check_installations", stdout=__import__("io").StringIO())
    notification = Notification.objects.get(user=admin, kind=Notification.APP_PERMISSIONS)
    assert "checks" in notification.params["missing"] and "push" in notification.params["events"]
    assert notification.url.endswith("/settings/apps/dashboard-test/permissions")
    from pycal_dashboard.github.permissions import EVENTS, REQUIRED

    github.app["permissions"], github.app["events"] = dict(REQUIRED), list(EVENTS)
    call_command("check_installations", stdout=__import__("io").StringIO())
    notification.refresh_from_db()
    assert notification.resolved is not None


def test_the_page_explains_the_two_steps(client, installation, bob):
    PermissionNotice(installation).send_if_needed()
    client.force_login(bob)
    page = client.get("/account/notifications/").content.decode()
    assert "If GitHub shows no request, the owners of the GitHub App add the permissions" in page
    assert "how-to/install-app.html#new-permissions" in page


def test_the_menu_does_not_install_the_app(client, bob):
    client.force_login(bob)
    menu = client.get("/projects/").content.decode().split('class="account-menu"')[1]
    assert "Install the GitHub App" not in menu.split("</details>")[0]


def test_an_installation_is_told_only_what_the_app_has(github, settings, db):
    """GitHub asks an installation to accept only what the app has: the app first."""
    import io

    from django.core.management import call_command

    from pycal_dashboard.github.permissions import EVENTS, REQUIRED
    from tests.conftest import person

    settings.SITE_ADMINS = ["admin"]
    admin = person(7, "admin")
    alice = person(42, "alice")
    lacking = {k: v for k, v in REQUIRED.items() if k not in ("checks", "statuses")}
    github.app["permissions"] = dict(lacking)  # the app lacks checks and statuses
    github.add_repository("collective/icalendar", installation=11)
    github.installations[0]["permissions"] = {"metadata": "read", "issues": "read"}
    Installation.objects.create(
        github_id=11,
        account_login="collective",
        account_type="Organization",
        admin_github_ids=["42"],
    )
    call_command("check_installations", stdout=io.StringIO())
    told = Notification.objects.get(user=alice, kind=Notification.PERMISSIONS)
    assert set(told.params["missing"]) == {"pull_requests", "contents"}  # not checks yet
    assert Notification.objects.filter(user=admin, kind=Notification.APP_PERMISSIONS).exists()
    github.app["permissions"], github.app["events"] = dict(REQUIRED), list(EVENTS)
    call_command("check_installations", stdout=io.StringIO())
    told.refresh_from_db()
    assert {"checks", "statuses"} <= set(told.params["missing"])  # now they can be accepted
    assert Notification.objects.get(user=admin, kind=Notification.APP_PERMISSIONS).resolved


def test_the_app_comes_first_and_read_ones_stay(client, installation, bob, settings):
    from pycal_dashboard.services.app_notice import AppNotice

    settings.SITE_ADMINS = ["bob"]
    PermissionNotice(installation).send_if_needed()

    class Lacking:
        complete = False
        app = {"slug": "dashboard-test"}
        missing_permissions = {"checks": "read"}
        missing_events = ["label"]
        settings_url = "https://github.com/organizations/PyCalendar/settings/apps/x/permissions"

    AppNotice(Lacking()).notify()
    client.force_login(bob)
    client.post("/account/notifications/", {"read": "all"})
    page = client.get("/account/notifications/").content.decode()
    first = page.index('data-notification="app_permissions"')
    assert first < page.index('data-notification="permissions"')  # the app first
    assert "data-notification-count" not in page  # read: not counted, but still shown


def test_the_app_lists_its_events_in_their_group(client, bob, settings):
    from pycal_dashboard.services.app_notice import AppNotice

    settings.SITE_ADMINS = ["bob"]

    class Lacking:
        complete = False
        app = {"slug": "dashboard-test"}
        missing_permissions = {"checks": "read", "statuses": "read"}
        missing_events = ["check_run", "push"]
        settings_url = "https://github.com/organizations/PyCalendar/settings/apps/x/permissions"

    AppNotice(Lacking()).notify()
    client.force_login(bob)
    page = client.get("/account/notifications/").content.decode()
    groups = page.split("data-permission-list>")[1].split("</ul></li></ul>")[0]
    assert groups.index("Repository permissions") < groups.index("Subscribe to events")
    assert '<span class="permission-name">Checks</span>: Read-only' in groups
    assert '<span class="permission-name">Commit statuses</span>' in groups
    assert '<span class="permission-name">Check run</span> <span class="muted">' in groups
    assert "Git push to a repository." in groups
