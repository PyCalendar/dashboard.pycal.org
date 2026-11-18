"""What followed from a trigger of the log, such as the rights of an administrator."""

from django.db import models

from .log_trigger import LogTrigger


class LogAction(models.Model):
    """What the site did and why, recorded by an :class:`~pycal_dashboard.actions.Action`."""

    trigger = models.ForeignKey(LogTrigger, on_delete=models.CASCADE, related_name="actions")
    kind = models.CharField(max_length=50)  # such as admin-rights, preferences, oauth-app
    text = models.CharField(max_length=500)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return self.text
