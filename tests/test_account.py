"""The private pages: account, preferences, email addresses and the webhook deliveries."""

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from pycal_dashboard.models import Profile, Repository
from tests.conftest import REPOSITORY, person


def test_account_needs_sign_in(client, db):
    response = client.get("/account/")
    assert response.status_code == 302 and response["Location"].startswith("/accounts/login/")


def test_account_page(client, synced, bob):
    EmailAddress.objects.create(user=bob, email="bob@example.org", verified=True, primary=True)
    client.force_login(bob)
    content = client.get("/account/").content.decode()
    assert "@bob" in content and "bob@example.org" in content
    assert "Pull request 4" in content  # bob is asked to review it


def test_save_preferences(client, synced, alice):
    client.force_login(alice)
    repository = Repository.objects.get(full_name=REPOSITORY)
    response = client.post(
        "/account/", {"email_digest": "yes", "days": "30", "watched": [str(repository.pk)]}
    )
    assert response.status_code == 302
    profile = Profile.objects.get(user=alice)
    assert profile.email_digest and profile.days == 30 and not profile.show_drafts
    assert list(profile.watched.all()) == [repository]
    assert "Repositories you watch" in client.get("/").content.decode()


def test_invalid_preferences(client, synced, alice):
    client.force_login(alice)
    response = client.post("/account/", {"days": "7"})
    assert response.status_code == 400 and b'data-error="UnknownPreference"' in response.content
    secret = Repository.objects.get(full_name="PyCalendar/secret")
    response = client.post("/account/", {"days": "90", "watched": [str(secret.pk)]})
    assert b'data-error="WatchedRepositoryUnknown"' in response.content


def test_account_without_github(client, db):
    user = get_user_model().objects.create(username="local")
    client.force_login(user)
    response = client.get("/account/")
    assert response.status_code == 403 and b'data-error="NoGitHubAccount"' in response.content


def test_email_page(client, alice):
    client.force_login(alice)
    response = client.get("/accounts/email/")
    assert response.status_code == 200 and b"Email addresses" in response.content


def test_deliveries_for_admins_only(client, admin, alice):
    client.force_login(alice)
    assert client.get("/account/deliveries/").status_code == 403
    client.force_login(admin)
    assert client.get("/account/deliveries/").status_code == 200


def test_site_admins_get_the_django_admin(client, db):
    from django.contrib.auth.signals import user_logged_in

    admin = person(7, "Admin")
    other = person(8, "other", is_staff=True, is_superuser=True)
    for user in (admin, other):
        user_logged_in.send(sender=type(user), request=None, user=user)
        user.refresh_from_db()
    assert admin.is_staff and admin.is_superuser
    assert not other.is_staff and not other.is_superuser


def test_sign_in_page(client, db):
    content = client.get("/accounts/login/").content.decode()
    assert "Sign in with GitHub" in content and "/accounts/github/login/" in content


def test_hide_drafts(client, synced, alice):
    from pycal_dashboard.models import Item

    Item.objects.filter(repository__full_name=REPOSITORY, number=4).update(draft=True)
    client.force_login(alice)
    assert "Pull request 4" in client.get(f"/repositories/{REPOSITORY}/").content.decode()
    client.post("/account/", {"days": "90"})  # show_drafts unchecked
    assert "Pull request 4" not in client.get(f"/repositories/{REPOSITORY}/").content.decode()
