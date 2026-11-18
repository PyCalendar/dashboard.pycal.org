"""Something that happened to the site, such as a webhook or a person signing in: the log."""

from django.db import models


class LogTrigger(models.Model):
    """A trigger of the log: a webhook of GitHub, or an action of a person or of the site.

    Its :class:`~pycal_dashboard.models.LogAction` records are what followed from it. The log
    is for the administrators of the site (``/logs/``).
    """

    kind = models.CharField(max_length=50)  # such as webhook, sign-in or setup
    summary = models.CharField(max_length=300)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_login = models.CharField(max_length=100, blank=True)
    repository = models.CharField(max_length=200, blank=True)  # the full name, of a webhook
    # the X-GitHub-Delivery of a webhook, to find it in the deliveries of the app
    delivery = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created", "-pk"]

    def __str__(self) -> str:
        return self.summary
