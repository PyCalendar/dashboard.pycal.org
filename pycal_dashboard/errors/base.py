"""The base of all errors."""

from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DashboardError(Exception):
    """Something went wrong.

    This is the base of all errors. If you see it, please report a bug with
    "Report a bug" at the bottom of the page.
    """

    title = _("Something went wrong")
    status = 400  # the HTTP status of the page that shows the error
    # a page of the documentation that explains the topic of the error; "" for none
    guide = "how-to/report-bug.html"
    guide_title = _("How to report a bug")

    def __init__(self, detail: str = "", **context):
        """An error people can meet, with what happened.

        Args:
            detail: What happened, shown after the title; the title if empty.
            **context: More about it, such as the repository.
        """
        super().__init__(detail or self.title)
        self.detail = detail
        self.context = context

    def __str__(self) -> str:
        return self.detail or self.title

    @property
    def code(self) -> str:
        """The name of the error, such as ``RepositoryNotFound``."""
        return type(self).__name__

    @classmethod
    def docs_url(cls) -> str:
        """The description of this error in the documentation.

        Returns:
            The address of the description.

        Examples:
            >>> UnexpectedError.docs_url().endswith(
            ...     "reference/errors.html#pycal_dashboard.errors.base.UnexpectedError")
            True
        """
        docs = settings.DOCS_URL.rstrip("/") + "/"
        return f"{docs}reference/errors.html#{cls.__module__}.{cls.__name__}"

    @classmethod
    def guide_url(cls) -> str:
        """The page of the documentation that explains the topic of the error.

        Returns:
            The address of the page, "" for errors without one.
        """
        docs = settings.DOCS_URL.rstrip("/") + "/"
        return f"{docs}{cls.guide}" if cls.guide else ""

    def as_json(self) -> dict:
        """The error for the API and the webhooks.

        Returns:
            ``error`` (the code), ``title``, ``detail`` and ``documentation``.
        """
        return {
            "error": self.code,
            "title": str(self.title),
            "detail": str(self),
            "documentation": self.docs_url(),
        }


class UnexpectedError(DashboardError):
    """An error that this site does not know.

    This is a bug. Please report it with "Report a bug" at the bottom of the
    page and include the details of the page.
    """

    title = _("Unexpected error")
    status = 500
