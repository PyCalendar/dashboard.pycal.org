"""The sign-in: a trigger of the log, the GitHub name in the profile, the Django admin.

The people of ``SITE_ADMINS`` get the Django admin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.http import HttpRequest

from .actions import Trigger
from .services.identity import GitHubIdentity

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser


@receiver(user_logged_in)
def admin_rights(
    sender: type, request: HttpRequest, user: AbstractBaseUser | AnonymousUser, **kwargs: Any
):
    """Log the sign-in; keep the GitHub name; give or take the rights of the Django admin.

    Parameters:
        sender: The class of the user.
        request: The request of the sign in.
        user: The user who signed in.
        **kwargs: More of the signal.
    """
    identity = GitHubIdentity.of(user)
    login = identity.login if identity else user.username
    with Trigger.start("sign-in", f"@{login} signed in", actor_login=login):
        GitHubIdentity.keep_profile(user)
        GitHubIdentity.keep_rights(user)
