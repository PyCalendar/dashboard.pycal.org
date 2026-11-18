"""The people of ``SITE_ADMINS`` get the rights of the Django admin when they sign in."""

from django.conf import settings
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
    if user.is_superuser and not user.socialaccount_set.exists():
        return  # an admin of manage.py createsuperuser
    identity = GitHubIdentity.of(user)
    admin = bool(identity and identity.login.lower() in settings.SITE_ADMINS)
    if user.is_staff != admin or user.is_superuser != admin:
        user.is_staff = user.is_superuser = admin
        user.save(update_fields=["is_staff", "is_superuser"])
