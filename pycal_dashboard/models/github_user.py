"""An account on GitHub that the site knows: who created issues and pull requests, who signs in."""

from django.conf import settings
from django.db import models

from .profile import Profile


class GitHubUser(models.Model):
    """An account on GitHub, by its id, which stays when the login changes.

    The site records the people who created issues and pull requests (``Issue.author``) and those
    who sign in. A ``User`` of the site is the person behind a GitHub user when they signed in
    with it (``user``, and ``user.github_user`` the other way); most GitHub users never sign in.
    The link is made by the id of GitHub, in :meth:`record`.
    """

    github_id = models.BigIntegerField("GitHub id", unique=True)
    login = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=200, blank=True)
    avatar_url = models.URLField(max_length=300, blank=True)
    # User, Bot or Organization, as GitHub says
    type = models.CharField(max_length=20, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="github_user",
    )

    class Meta:
        ordering = ["login"]
        verbose_name = "GitHub user"

    def __str__(self) -> str:
        return f"@{self.login}"

    @property
    def url(self) -> str:
        """The account on GitHub."""
        return f"https://github.com/{self.login}"

    @classmethod
    def record(cls, data: dict, user=None) -> "GitHubUser | None":
        """Keep an account as GitHub describes it, such as the ``user`` of an issue.

        The account is linked to the user of the site who signed in with it: the given one, or
        the one whose profile has its GitHub id.

        Args:
            data: The account from GitHub: ``id``, ``login``, ``avatar_url``, ``type`` and
                ``name`` if GitHub gives them.
            user: The user of the site who signed in with it, None if not known.

        Returns:
            The GitHub user, None without an id.
        """
        github_id = data.get("id")
        if not github_id:
            return None
        fields = {"login": str(data.get("login") or "")}
        for name in ("avatar_url", "type", "name"):
            if data.get(name):
                fields[name] = str(data[name])
        if user is None:
            profile = Profile.objects.filter(github_id=str(github_id)).first()
            user = profile.user if profile else None
        if user is not None:
            cls.objects.filter(user=user).exclude(github_id=github_id).update(user=None)
            fields["user"] = user
        found, _created = cls.objects.update_or_create(github_id=github_id, defaults=fields)
        return found
