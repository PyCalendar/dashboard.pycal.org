"""The GitHub account of a person who signed in."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings

from pycal_dashboard.import_guard import IMPORT_GUARD

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser


@dataclass(frozen=True)
class GitHubIdentity:
    """The login and id of GitHub of a user of the site."""

    login: str
    github_id: str
    avatar_url: str = ""

    @classmethod
    def of(cls, user: AbstractBaseUser | AnonymousUser) -> GitHubIdentity | None:
        """The GitHub account of a user.

        Parameters:
            user: A user of Django, or None.

        Returns:
            The identity, or None for visitors and accounts without GitHub.
        """
        if not getattr(user, "is_authenticated", False):
            return None
        account = user.socialaccount_set.filter(provider="github").first()
        if account is None:
            return None
        data = account.extra_data or {}
        return cls(str(data.get("login") or user.username), account.uid, data.get("avatar_url", ""))

    @classmethod
    def keep_profile(cls, user: AbstractBaseUser | AnonymousUser):
        """Keep the GitHub name and id of a person in their profile, and their GitHub user.

        A person who renamed their account on GitHub gets the new name at the next sign in.

        Parameters:
            user: The user who signed in.

        Returns:
            The profile, None for accounts without GitHub.
        """
        identity = cls.of(user)
        if identity is None:
            return None
        with IMPORT_GUARD:  # see import_guard.py
            from pycal_dashboard.models import GitHubUser, Profile

        profile, _created = Profile.objects.get_or_create(user=user)
        if (profile.github_name, profile.github_id) != (identity.login, identity.github_id):
            profile.github_name, profile.github_id = identity.login, identity.github_id
            profile.save(update_fields=["github_name", "github_id"])
        account = user.socialaccount_set.filter(provider="github").first()
        data = dict(account.extra_data or {}) if account else {}
        if identity.github_id.isdigit():  # the person behind the GitHub user
            data.update(id=int(identity.github_id), login=identity.login)
            GitHubUser.record(data, user=user)
        return profile

    @staticmethod
    def is_site_admin(user: AbstractBaseUser | AnonymousUser) -> bool:
        """Whether a user administers the site: ``SITE_ADMINS`` or a superuser.

        Parameters:
            user: A user of Django.

        Returns:
            True for the administrators.
        """
        if not getattr(user, "is_authenticated", False):
            return False
        if user.is_superuser:
            return True
        identity = GitHubIdentity.of(user)
        return bool(identity and identity.login.lower() in settings.SITE_ADMINS)

    @classmethod
    def rights_differ(cls, user: AbstractBaseUser | AnonymousUser) -> bool:
        """Whether the rights of the Django admin of a person differ from ``SITE_ADMINS``.

        Parameters:
            user: The user.

        Returns:
            True if :meth:`keep_rights` would change them.
        """
        identity = cls.of(user)
        if identity is None:
            return False
        admin = identity.login.lower() in settings.SITE_ADMINS
        return user.is_staff != admin or user.is_superuser != admin

    @classmethod
    def keep_rights(cls, user: AbstractBaseUser | AnonymousUser) -> bool:
        """Give the people of ``SITE_ADMINS`` the rights of the Django admin, and only them.

        Users without a GitHub account, such as one of ``createsuperuser``, keep their rights.

        Parameters:
            user: The user.

        Returns:
            True if the rights changed.
        """
        identity = cls.of(user)
        if identity is None:
            return False
        admin = identity.login.lower() in settings.SITE_ADMINS
        if user.is_staff == admin and user.is_superuser == admin:
            return False
        user.is_staff = user.is_superuser = admin
        user.save(update_fields=["is_staff", "is_superuser"])
        with IMPORT_GUARD:  # see import_guard.py
            from pycal_dashboard.actions import AdminRightsChanged

        AdminRightsChanged(identity.login, admin).run()
        return True
