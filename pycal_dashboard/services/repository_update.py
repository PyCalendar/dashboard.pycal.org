"""Update a repository from GitHub: whether it is private, its issues and pull requests."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from pycal_dashboard.conditions import DATA_SPECS, LabelsData
from pycal_dashboard.errors import DashboardError, translate
from pycal_dashboard.github.client import GitHubClient
from pycal_dashboard.github.data_version import DATA_VERSION
from pycal_dashboard.github.installation_token import InstallationToken
from pycal_dashboard.github.queries import PULL_REQUESTS
from pycal_dashboard.models import GitHubUser, Issue, Repository
from pycal_dashboard.update_signals import repository_updated

from .installation_store import InstallationStore

if TYPE_CHECKING:
    import httpx

LAST_PAGE = re.compile(r'[?&]page=(\d+)[^>]*>;\s*rel="last"')
log = logging.getLogger(__name__)
PER_PAGE = 100  # the most that GitHub gives on a page
# the open pull requests of a page of GraphQL; down to the least when GitHub gives up
PULL_REQUESTS_PER_PAGE = 20
MIN_PULL_REQUESTS_PER_PAGE = 5
MAX_PAGES = 500  # 50 000 issues and pull requests of a repository at most


class RepositoryUpdate:
    """One update of a repository, in the background (``UpdateJob``).

    With the GitHub App installed on it, the site reads with the token of the installation, also
    private repositories; else without a token, which sees public repositories.

    The issues and pull requests are read completely the first time and when the version of what
    the site keeps of GitHub is newer (:data:`DATA_VERSION`); else only those that changed since
    the last update.
    """

    def __init__(self, repository: Repository):
        """An update of a repository.

        Parameters:
            repository: The repository.
        """
        self.repository = repository
        self.people: dict[int, GitHubUser | None] = {}  # the authors recorded, by their id
        self.read_completely = False  # whether this update read all issues, see issues()

    @staticmethod
    def count(response: httpx.Response) -> int:
        """The number of items of a list of GitHub read with one item per page.

        Parameters:
            response: The answer to a request with ``per_page=1``.

        Returns:
            The number of items: the number of the last page.
        """
        found = LAST_PAGE.search(response.headers.get("link", ""))
        return int(found[1]) if found else len(response.json())

    def client(self) -> GitHubClient:
        """The client that reads the repository, and its installation recorded.

        Returns:
            A client with the token of the installation, else without a token.
        """
        installation = InstallationToken.installation_of(self.repository.full_name)
        self.repository.installation = (
            InstallationStore.record(installation) if installation else None
        )
        return InstallationToken.client(installation["id"]) if installation else GitHubClient()

    def run(self) -> bool:
        """Read the repository and keep what GitHub says, or the error.

        Returns:
            True if it was updated, False if an error was kept.
        """
        repository = self.repository
        try:
            client = self.client()
            data = client.request("GET", f"/repos/{repository.full_name}").json()
            pulls = self.count(
                client.request(
                    "GET",
                    f"/repos/{repository.full_name}/pulls",
                    params={"state": "open", "per_page": 1},
                )
            )
            self.issues(client)
            for spec in DATA_SPECS:  # what the conditions need, which the app may read
                if spec.enabled(self.granted()):
                    spec.fetch(client, repository)
            self.pull_requests(client)
        except Exception as exception:  # every error is kept and shown on the project
            error: DashboardError = translate(exception)
            repository.error_code, repository.error_detail = error.code, str(error)[:500]
            repository.error_at = timezone.now()
            repository.save()
            return False
        if self.read_completely:  # all data of this version, also of the pull requests
            repository.data_version = DATA_VERSION
        repository.full_name = data.get("full_name") or repository.full_name  # renamed
        repository.github_id = data.get("id") or repository.github_id
        repository.private = bool(data.get("private"))
        repository.description = data.get("description") or ""
        # GitHub counts the open pull requests among the open issues
        repository.open_pull_requests = pulls
        repository.open_issues = max(0, int(data.get("open_issues_count") or 0) - pulls)
        repository.error_code = repository.error_detail = ""
        repository.error_at = None
        repository.updated = timezone.now()
        repository.save()
        repository_updated.send(sender=RepositoryUpdate, repository=repository)
        return True

    def complete(self) -> bool:
        """Whether the issues are read completely, not only those changed since the last time."""
        repository = self.repository
        return repository.data_version < DATA_VERSION or repository.issues_changed is None

    def issues(self, client: GitHubClient) -> int:
        """Read the issues and pull requests, open and closed, and keep them.

        After a complete reading, those that GitHub no longer has, such as deleted or
        transferred ones, are removed; when the whole update works, the repository has the data
        of :data:`DATA_VERSION`.

        Parameters:
            client: The client that reads the repository.

        Returns:
            How many were read.
        """
        repository = self.repository
        complete = self.complete()
        params = {"state": "all", "sort": "updated", "direction": "asc", "per_page": PER_PAGE}
        if not complete:
            params["since"] = repository.issues_changed.isoformat()
        seen: set[int] = set()
        # without any issue yet, the next update reads what changed from the start of this one
        started = timezone.now()
        changed = repository.issues_changed
        for page in range(1, MAX_PAGES + 1):
            items = client.request(
                "GET", f"/repos/{repository.full_name}/issues", params={**params, "page": page}
            ).json()
            with transaction.atomic():
                for item in items:
                    issue = self.keep(item)
                    seen.add(issue.number)
                    if issue.changed and (changed is None or issue.changed > changed):
                        changed = issue.changed
            if len(items) < PER_PAGE:
                break
        with transaction.atomic():
            if complete:
                repository.issues.exclude(number__in=seen).delete()
                self.read_completely = True  # the version follows when all of the update worked
            repository.issues_changed = changed or started
            repository.save(update_fields=["issues_changed"])
        return len(seen)

    def keep(self, item: dict) -> Issue:
        """Keep an issue or a pull request as GitHub describes it.

        Parameters:
            item: An issue of the list of GitHub; a pull request has ``pull_request``.

        Returns:
            The issue, saved.
        """
        pull_request = item.get("pull_request") or None
        merged = (pull_request or {}).get("merged_at")
        issue, _created = Issue.objects.update_or_create(
            repository=self.repository,
            number=int(item["number"]),
            defaults={
                "github_id": item.get("id"),
                "pull_request": pull_request is not None,
                "title": str(item.get("title") or "")[:500],
                "author": self.author(item.get("user") or {}),
                "description": str(item.get("body") or ""),
                "author_association": str(item.get("author_association") or "")[:30],
                "state": Issue.CLOSED if item.get("state") == "closed" else Issue.OPEN,
                "created": parse_datetime(item["created_at"]),
                "closed": parse_datetime(item["closed_at"]) if item.get("closed_at") else None,
                "merged": parse_datetime(merged) if merged else None,
                "changed": parse_datetime(item["updated_at"]) if item.get("updated_at") else None,
            },
        )
        LabelsData.keep(issue, item)
        return issue

    def author(self, data: dict) -> GitHubUser | None:
        """The GitHub user who created an issue, recorded once in an update.

        Parameters:
            data: The ``user`` of the issue.

        Returns:
            The GitHub user, None if GitHub does not say.
        """
        github_id = data.get("id")
        if github_id not in self.people:
            self.people[github_id] = GitHubUser.record(data)
        return self.people[github_id]

    def granted(self) -> dict[str, str] | None:
        """The permissions that the owners of the installation of the repository accepted.

        Returns:
            The permissions; None without an installation that the site recorded them of.
        """
        installation = self.repository.installation
        return dict(installation.permissions) if installation and installation.permissions else None

    def pull_requests(self, client: GitHubClient) -> int:
        """Read the open pull requests with one query of GraphQL for what the conditions need.

        The fields are those of the data specs that the installation may read
        (``DataSpec.graphql``); a page costs about one point of GitHub. GitHub gives up on a
        query that takes too long, such as whether many pull requests can be merged: then the
        same page is asked again with half as many. GraphQL needs a token, so only repositories
        with the GitHub App are read.

        Parameters:
            client: The client of the installation.

        Returns:
            How many pull requests were read.
        """
        repository = self.repository
        if not repository.app_installed:
            return 0
        specs = [spec for spec in DATA_SPECS if spec.enabled(self.granted()) and spec.graphql]
        if not specs:
            return 0
        query = PULL_REQUESTS.replace("FIELDS", " ".join(spec.graphql for spec in specs))
        owner, name = repository.full_name.split("/", 1)
        issues = {
            issue.number: issue
            for issue in Issue.objects.filter(
                repository=repository, pull_request=True, state=Issue.OPEN
            )
        }
        read = 0
        for nodes in client.graphql_pages(
            query,
            ("repository", "pullRequests"),
            PULL_REQUESTS_PER_PAGE,
            MIN_PULL_REQUESTS_PER_PAGE,
            owner=owner,
            name=name,
        ):
            for node in nodes:
                issue = issues.get(node["number"])
                if issue is None:  # opened after the issues were read: the next update
                    continue
                for spec in specs:
                    spec.keep_pull_request(issue, node)
                read += 1
        log.info("%s: %s pull requests, rate %s", repository.full_name, read, client.rate)
        return read
