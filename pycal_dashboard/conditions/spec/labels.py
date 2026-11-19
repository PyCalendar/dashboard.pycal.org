"""The labels of a repository and of its pull requests."""

from pycal_dashboard.conditions.spec.base import DataSpec
from pycal_dashboard.github.data_version import DATA_VERSION
from pycal_dashboard.models import Label

PER_PAGE = 100


class LabelsData(DataSpec):
    """The labels of a repository, with description and color, and those of its pull requests.

    The labels of a pull request come with its issue (``RepositoryUpdate.keep`` calls
    :meth:`keep`); :meth:`fetch` reads all labels of the repository, also those that no pull
    request has.
    """

    id = "labels"
    title = "The labels of the repository and of the pull request"
    permissions = {"metadata": "read", "issues": "read"}
    events = ("issues", "pull_request")

    def fetch(self, client, repository) -> int:
        """Read all labels of the repository; remove those it no longer has.

        Args:
            client: The client.
            repository: The repository.

        Returns:
            How many labels it has.
        """
        seen = []
        for page in range(1, 51):
            items = client.request(
                "GET",
                f"/repos/{repository.full_name}/labels",
                params={"per_page": PER_PAGE, "page": page},
            ).json()
            seen.extend(self.label(repository, item).pk for item in items)
            if len(items) < PER_PAGE:
                break
        repository.labels.exclude(pk__in=seen).delete()
        return len(seen)

    @staticmethod
    def label(repository, item: dict) -> Label:
        """Keep a label as GitHub describes it.

        Args:
            repository: The repository.
            item: The label: ``id``, ``name``, ``description`` and ``color``.

        Returns:
            The label.
        """
        label, _created = Label.objects.update_or_create(
            repository=repository,
            name=str(item["name"])[:100],
            defaults={
                "github_id": item.get("id"),
                "description": str(item.get("description") or "")[:300],
                "color": str(item.get("color") or "")[:6],
            },
        )
        return label

    @classmethod
    def keep(cls, issue, item: dict) -> None:
        """Keep the labels of an issue or pull request from its item of GitHub.

        Args:
            issue: The issue, saved.
            item: The issue as GitHub lists it, with ``labels``.
        """
        labels = [
            cls.label(issue.repository, label)
            for label in item.get("labels") or []
            if isinstance(label, dict) and label.get("name")
        ]
        issue.labels.set(labels)

    def complete(self, issue) -> bool:
        """The labels are kept with the issues since data version 2.

        Args:
            issue: The pull request.

        Returns:
            True if the repository was read with the current data version.
        """
        return issue.repository.data_version >= DATA_VERSION
