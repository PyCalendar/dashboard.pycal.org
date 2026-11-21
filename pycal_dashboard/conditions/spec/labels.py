"""The labels of a repository and of its pull requests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext

from pycal_dashboard.conditions.evidence import Evidence
from pycal_dashboard.conditions.spec.base import DataSpec
from pycal_dashboard.github.data_version import DATA_VERSION
from pycal_dashboard.import_guard import IMPORT_GUARD
from pycal_dashboard.models import Label

if TYPE_CHECKING:
    from pycal_dashboard.github.client import GitHubClient
    from pycal_dashboard.models import Issue, Repository


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
    events = ("label", "issues", "pull_request")

    def fetch(self, client: GitHubClient, repository: Repository) -> int:
        """Read all labels of the repository; remove those it no longer has.

        Parameters:
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
    def label(repository: Repository, item: dict) -> Label:
        """Keep a label as GitHub describes it; a renamed one, found by its id, is renamed.

        The saved filters that name a renamed label are renamed too (``LabelRename``).

        Parameters:
            repository: The repository.
            item: The label: ``id``, ``name``, ``description`` and ``color``.

        Returns:
            The label.
        """
        name = str(item["name"])[:100]
        details = {
            "description": str(item.get("description") or "")[:300],
            "color": str(item.get("color") or "")[:6],
        }
        renamed = None
        if item.get("id"):  # GitHub keeps the id of a renamed label
            renamed = repository.labels.filter(github_id=item["id"]).exclude(name=name).first()
        if renamed is not None:
            old = renamed.name
            repository.labels.filter(name=name).exclude(pk=renamed.pk).delete()
            Label.objects.filter(pk=renamed.pk).update(name=name, **details)
            renamed.refresh_from_db()
            with IMPORT_GUARD:  # see import_guard.py; the service imports the conditions
                from pycal_dashboard.services.label_rename import LabelRename

            LabelRename(repository, old, name).apply()
            return renamed
        label, _created = Label.objects.update_or_create(
            repository=repository,
            name=name,
            defaults={"github_id": item.get("id"), **details},
        )
        return label

    @classmethod
    def keep(cls, issue: Issue, item: dict) -> None:
        """Keep the labels of an issue or pull request from its item of GitHub.

        Parameters:
            issue: The issue, saved.
            item: The issue as GitHub lists it, with ``labels``.
        """
        labels = [
            cls.label(issue.repository, label)
            for label in item.get("labels") or []
            if isinstance(label, dict) and label.get("name")
        ]
        issue.labels.set(labels)

    def evidence(self, issue: Issue) -> list[Evidence]:
        """The labels of the pull request, at the right of its page on GitHub.

        Parameters:
            issue: The pull request.

        Returns:
            The link to it.
        """
        return [Evidence(gettext("Its labels on GitHub"), issue.url)]

    def complete(self, issue: Issue) -> bool:
        """The labels are kept with the issues since data version 2.

        Parameters:
            issue: The pull request.

        Returns:
            True if the repository was read with the current data version.
        """
        return issue.repository.data_version >= DATA_VERSION
