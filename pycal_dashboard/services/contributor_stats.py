"""The public activity of one person in the repositories of the dashboard."""

from django.db.models import Min

from pycal_dashboard.errors import ContributorNotFound

from .overview import Overview


class ContributorStats:
    """What a person opened, what was merged and what waits for them; public data only."""

    def __init__(self, login: str, overview: Overview | None = None):
        """The statistics of a person.

        Args:
            login: The GitHub handle.
            overview: The repositories to count; all public ones by default.

        Raises:
            ContributorNotFound: The person opened nothing in these repositories.
        """
        self.overview = overview or Overview()
        self.items = self.overview.items().filter(author_login__iexact=login)
        first = self.items.first()
        if first is None:
            raise ContributorNotFound(login)
        self.login = first.author_login

    def numbers(self) -> dict:
        """The totals.

        Returns:
            ``pulls``, ``merged``, ``issues``, ``repositories`` and ``since``.
        """
        return {
            "pulls": self.items.filter(is_pull=True).count(),
            "merged": self.items.filter(merged=True).count(),
            "issues": self.items.filter(is_pull=False).count(),
            "repositories": self.items.values("repository").distinct().count(),
            "since": self.items.aggregate(first=Min("created_at"))["first"],
        }

    def open_pulls(self):
        """The open pull requests of the person.

        Returns:
            The pull requests, the latest activity first.
        """
        return self.items.filter(is_pull=True, state="open").order_by("-updated_at")

    def review_requests(self):
        """Open pull requests where the person is asked for a review.

        Returns:
            The pull requests, the longest waiting first.
        """
        return [
            item
            for item in self.overview.open_pulls().order_by("updated_at")
            if self.login.lower() in {login.lower() for login in item.requested_reviewers}
        ]

    def recent(self, limit: int = 20):
        """The latest issues and pull requests of the person.

        Args:
            limit: How many.

        Returns:
            The items.
        """
        return self.items.order_by("-created_at")[:limit]
