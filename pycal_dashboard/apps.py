"""The Django app of the site."""

from django.apps import AppConfig

from pycal_dashboard.import_guard import IMPORT_GUARD


class DashboardConfig(AppConfig):
    """The app: models, templates and commands."""

    name = "pycal_dashboard"
    verbose_name = "Dashboard"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Connect the signals and register the checks of the settings."""
        with IMPORT_GUARD:  # see import_guard.py
            from . import checks, receivers, signals  # noqa: F401
