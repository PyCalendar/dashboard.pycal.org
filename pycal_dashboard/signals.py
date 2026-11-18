"""The sign-in: a trigger of the log; the people of ``SITE_ADMINS`` get the Django admin."""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .actions import Trigger
from .services.identity import GitHubIdentity


@receiver(user_logged_in)
def admin_rights(sender, request, user, **kwargs):
    """Log the sign-in; give or take the rights of the Django admin, as ``SITE_ADMINS`` says.

    Args:
        sender: The class of the user.
        request: The request of the sign in.
        user: The user who signed in.
        **kwargs: More of the signal.
    """
    identity = GitHubIdentity.of(user)
    login = identity.login if identity else user.username
    with Trigger.start("sign-in", f"@{login} signed in", actor_login=login):
        GitHubIdentity.keep_rights(user)
