"""The people of ``SITE_ADMINS`` get the rights of the Django admin when they sign in."""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .services.identity import GitHubIdentity


@receiver(user_logged_in)
def admin_rights(sender, request, user, **kwargs):
    """Give or take the rights of the Django admin, as ``SITE_ADMINS`` says.

    Args:
        sender: The class of the user.
        request: The request of the sign in.
        user: The user who signed in.
        **kwargs: More of the signal.
    """
    GitHubIdentity.keep_rights(user)
