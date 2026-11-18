"""The Django app of the site."""

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """The app: models, templates and commands."""

    name = "pycal_dashboard"
    verbose_name = "Dashboard"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Connect the signals."""
        from . import signals  # noqa: F401
