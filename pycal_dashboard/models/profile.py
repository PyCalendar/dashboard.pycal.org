"""The names of a person on the platforms of code, such as GitHub."""

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """The public names of a person who signed in, by platform.

    The GitHub name is the handle on GitHub, taken at every sign in with GitHub. Other platforms,
    such as GitLab, get their own fields: a name is always that of one platform.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    github_name = models.CharField("GitHub name", max_length=39, blank=True, db_index=True)
    github_id = models.CharField("GitHub id", max_length=30, blank=True, db_index=True)

    def __str__(self) -> str:
        return f"@{self.github_name}" if self.github_name else str(self.user)

    @classmethod
    def with_github_name(cls, name: str) -> "Profile | None":
        """The profile with a GitHub name, in any case.

        Parameters:
            name: The GitHub name, with or without ``@``.

        Returns:
            The profile, None if nobody with this name signed in.
        """
        name = name.strip().removeprefix("@")
        if not name:
            return None
        return cls.objects.select_related("user").filter(github_name__iexact=name).first()
