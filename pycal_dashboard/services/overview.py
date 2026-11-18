"""The numbers and lists of the dashboard, from the public repositories only."""

from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from pycal_dashboard.models import Item, Repository

# labels that invite new contributors, in lower case
STARTER_LABELS = {"good first issue", "good-first-issue", "help wanted", "help-wanted", "easy"}


class Overview:
    """What the dashboard shows: public repositories of shown installations only."""

    def __init__(self, days: int = 90, repositories: QuerySet | None = None):
        """An overview.

        Args:
            days: The period of the statistics, such as merged pull requests.
            repositories: Only these repositories; all public ones by default.
        """
        self.days = days
        self.since = timezone.now() - timedelta(days=days)
        self.repositories = self.public() if repositories is None else repositories

    @staticmethod
    def public() -> QuerySet:
        """The repositories that the dashboard shows.

        Returns:
            Public repositories of an installation, not archived first.
        """
        return Repository.objects.filter(private=False, installation__isnull=False).order_by(
            "archived", "full_name"
        )

    def items(self) -> QuerySet:
        """The issues and pull requests of the repositories.

        Returns:
            The items.
        """
        return Item.objects.filter(repository__in=self.repositories).select_related("repository")

    def open_pulls(self) -> QuerySet:
        """The open pull requests.

        Returns:
            The pull requests.
        """
        return self.items().filter(is_pull=True, state="open")

    def open_issues(self) -> QuerySet:
        """The open issues.

        Returns:
            The issues.
        """
        return self.items().filter(is_pull=False, state="open")

    def starter_issues(self, limit: int | None = None) -> list[Item]:
        """Open issues with a label for newcomers, such as ``good first issue``.

        Args:
            limit: The most to return; all by default.

        Returns:
            The issues, newest first.
        """
        found = [
            item
            for item in self.open_issues().order_by("-created_at")
            if STARTER_LABELS & {label.lower() for label in item.labels}
        ]
        return found[:limit] if limit else found

    def waiting_for_review(self) -> QuerySet:
        """Open pull requests that are ready for a review, the longest waiting first.

        Returns:
            The pull requests, not drafts and not of bots.
        """
        return self.open_pulls().filter(draft=False, author_is_bot=False).order_by("updated_at")

    def unanswered(self) -> QuerySet:
        """Open issues without a comment, the oldest first.

        Returns:
            The issues, not of bots.
        """
        return self.open_issues().filter(comments=0, author_is_bot=False).order_by("created_at")

    def stale(self) -> QuerySet:
        """Open pull requests without activity for ``STALE_DAYS`` days.

        Returns:
            The pull requests, the oldest activity first.
        """
        limit = timezone.now() - timedelta(days=settings.STALE_DAYS)
        return self.open_pulls().filter(updated_at__lt=limit).order_by("updated_at")

    def merged(self) -> QuerySet:
        """Pull requests merged in the period, the latest first.

        Returns:
            The pull requests.
        """
        return self.items().filter(merged=True, merged_at__gte=self.since).order_by("-merged_at")

    def contributors(self, limit: int | None = None) -> list[dict]:
        """The people who opened issues or pull requests in the period, the most active first.

        Args:
            limit: The most to return.

        Returns:
            ``login``, ``pulls``, ``merged`` and ``issues`` of each person; bots are left out.
        """
        rows = (
            self.items()
            .filter(created_at__gte=self.since, author_is_bot=False)
            .values("author_login")
            .annotate(
                pulls=Count("pk", filter=Q(is_pull=True)),
                merged=Count("pk", filter=Q(merged=True)),
                issues=Count("pk", filter=Q(is_pull=False)),
                total=Count("pk"),
            )
            .order_by("-merged", "-total", "author_login")
        )
        found = [
            {"login": row["author_login"], **{k: row[k] for k in ("pulls", "merged", "issues")}}
            for row in rows
        ]
        return found[:limit] if limit else found

    def first_contributions(self) -> QuerySet:
        """Pull requests of people who contributed for the first time, in the period.

        Returns:
            The pull requests, the latest first.
        """
        return (
            self.items()
            .filter(
                is_pull=True,
                created_at__gte=self.since,
                author_association__in=["FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER"],
            )
            .order_by("-created_at")
        )

    def counts(self) -> dict:
        """The numbers at the top of the start page.

        Returns:
            Repositories, open issues and pull requests, issues for newcomers, pull requests
            waiting for a review, merged ones and contributors in the period.
        """
        return {
            "repositories": self.repositories.filter(archived=False).count(),
            "open_issues": self.open_issues().count(),
            "open_pulls": self.open_pulls().count(),
            "starter_issues": len(self.starter_issues()),
            "waiting_for_review": self.waiting_for_review().count(),
            "unanswered": self.unanswered().count(),
            "merged": self.merged().count(),
            "contributors": len(self.contributors()),
            "days": self.days,
        }

    def per_repository(self) -> list[dict]:
        """The numbers of each repository.

        Returns:
            ``repository``, ``open_issues``, ``open_pulls``, ``waiting`` and ``merged``.
        """
        rows = {
            row["repository"]: row
            for row in self.items()
            .values("repository")
            .annotate(
                open_issues=Count("pk", filter=Q(is_pull=False, state="open")),
                open_pulls=Count("pk", filter=Q(is_pull=True, state="open")),
                waiting=Count(
                    "pk", filter=Q(is_pull=True, state="open", draft=False, author_is_bot=False)
                ),
                merged=Count("pk", filter=Q(merged=True, merged_at__gte=self.since)),
            )
        }
        empty = {"open_issues": 0, "open_pulls": 0, "waiting": 0, "merged": 0}
        return [
            {"repository": repository, **{k: rows.get(repository.pk, empty)[k] for k in empty}}
            for repository in self.repositories
        ]
