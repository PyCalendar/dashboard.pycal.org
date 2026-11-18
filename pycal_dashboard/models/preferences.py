"""The private preferences of a person who signed in: the language and the colors."""

from django.conf import settings
from django.db import models


class Preferences(models.Model):
    """What a person chose on the page Account or in the menus; nobody else sees it.

    An empty choice leaves it to the browser: its language (``Accept-Language``) or the
    choice of the menu in a cookie, and the colors of the system.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_preferences"
    )
    language = models.CharField(max_length=10, blank=True, default="")  # such as de; "": browser
    theme = models.CharField(max_length=10, blank=True, default="")  # auto, light, dark; "": cookie

    class Meta:
        verbose_name_plural = "preferences"

    def __str__(self) -> str:
        return f"preferences of {self.user}"

    @classmethod
    def of(cls, user) -> "Preferences | None":
        """The preferences of a person.

        Args:
            user: A user of Django, or a visitor.

        Returns:
            The saved preferences; None for visitors and people who chose nothing yet.
        """
        if not getattr(user, "is_authenticated", False):
            return None
        return cls.objects.filter(user=user).first()
