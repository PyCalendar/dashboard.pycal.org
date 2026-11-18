"""The GitHub account of a person who signed in."""

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class GitHubIdentity:
    """The login and id of GitHub of a user of the site."""

    login: str
    github_id: str
    avatar_url: str = ""

    @classmethod
    def of(cls, user) -> "GitHubIdentity | None":
        """The GitHub account of a user.

        Args:
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

    @staticmethod
    def is_site_admin(user) -> bool:
        """Whether a user administers the site: ``SITE_ADMINS`` or a superuser.

        Args:
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
    def rights_differ(cls, user) -> bool:
        """Whether the rights of the Django admin of a person differ from ``SITE_ADMINS``.

        Args:
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
    def keep_rights(cls, user) -> bool:
        """Give the people of ``SITE_ADMINS`` the rights of the Django admin, and only them.

        Users without a GitHub account, such as one of ``createsuperuser``, keep their rights.

        Args:
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
        from pycal_dashboard.actions import AdminRightsChanged

        AdminRightsChanged(identity.login, admin).run()
        return True
