"""Store the issues, pull requests and repositories that GitHub describes."""

from datetime import datetime

from django.utils import timezone

from pycal_dashboard.models import Item, Repository


def parse_time(value: str | None) -> datetime | None:
    """A time of GitHub.

    Args:
        value: Such as ``2026-11-18T09:30:00Z``, or None.

    Returns:
        The time with its time zone, or None.

    Examples:
        >>> parse_time("2026-11-18T09:30:00Z").isoformat()
        '2026-11-18T09:30:00+00:00'
        >>> parse_time(None) is None
        True
    """
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ItemStore:
    """Writes what GitHub says into the database."""

    @staticmethod
    def repository(data: dict, installation=None) -> Repository:
        """Create or update a repository.

        Args:
            data: The repository as GitHub describes it.
            installation: The installation it belongs to; None keeps the known one.

        Returns:
            The repository.
        """
        fields = {
            "full_name": data["full_name"],
            "description": data.get("description") or "",
            "html_url": data.get("html_url") or f"https://github.com/{data['full_name']}",
            "private": bool(data.get("private")),
            "archived": bool(data.get("archived")),
            "fork": bool(data.get("fork")),
            "default_branch": data.get("default_branch") or "main",
            "language": data.get("language") or "",
            "topics": data.get("topics") or [],
            "stars": data.get("stargazers_count") or 0,
            "forks": data.get("forks_count") or 0,
            "pushed_at": parse_time(data.get("pushed_at")),
        }
        if installation is not None:
            fields["installation"] = installation
        repository, _ = Repository.objects.update_or_create(github_id=data["id"], defaults=fields)
        return repository

    @staticmethod
    def item(repository: Repository, data: dict) -> Item:
        """Create or update an issue or a pull request.

        Args:
            repository: Its repository.
            data: The issue or pull request as GitHub describes it, from the API of the
                issues or of the pull requests.

        Returns:
            The item.
        """
        is_pull = "pull_request" in data or "head" in data
        pull_info = data.get("pull_request") or {}
        merged_at = data.get("merged_at") or pull_info.get("merged_at")
        user = data.get("user") or {}
        labels = [
            label["name"] if isinstance(label, dict) else label for label in data.get("labels", [])
        ]
        fields = {
            "is_pull": is_pull,
            "title": (data.get("title") or "")[:500],
            "state": data.get("state") or "open",
            "draft": bool(data.get("draft")),
            "merged": bool(data.get("merged") or merged_at),
            "author_login": user.get("login") or "ghost",
            "author_association": data.get("author_association") or "",
            "author_is_bot": user.get("type") == "Bot",
            "labels": labels,
            "comments": data.get("comments") or 0,
            "html_url": data.get("html_url") or "",
            "created_at": parse_time(data.get("created_at")) or timezone.now(),
            "updated_at": parse_time(data.get("updated_at")) or timezone.now(),
            "closed_at": parse_time(data.get("closed_at")),
            "merged_at": parse_time(merged_at),
        }
        if "requested_reviewers" in data:
            fields["requested_reviewers"] = [
                person["login"] for person in data["requested_reviewers"] if person
            ]
        for count in ("additions", "deletions"):
            if isinstance(data.get(count), int):
                fields[count] = data[count]
        item, _ = Item.objects.update_or_create(
            repository=repository, number=data["number"], defaults=fields
        )
        return item
