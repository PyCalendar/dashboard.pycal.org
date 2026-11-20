"""The results of the columns of conditions for all pull requests of a project, cached."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from django.core.cache import cache
from django.db.models import prefetch_related_objects

from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.models import Issue

if TYPE_CHECKING:
    from pycal_dashboard.conditions.group.column import Column
    from pycal_dashboard.models import Repository

CACHED_SECONDS = 24 * 3600  # the key changes with every update of a repository


class ColumnResults:
    """Whether each column applies to each pull request of repositories, kept in the cache.

    A column is evaluated for all pull requests at once, with the data they need loaded in a
    few queries, and its results are kept in the cache of Django under the version of the
    repositories: when they were updated and read. An update of a repository makes a new
    version, so nothing is evaluated again until GitHub changed something. A page of the table
    then loads only the pull requests it shows (:meth:`rows`).
    """

    def __init__(self, repositories: list[Repository], scope: Scope | None = None):
        """The pull requests of repositories.

        Parameters:
            repositories: The repositories that the person sees.
            scope: Where the states of the authors are counted; the repositories by default.
        """
        self.repositories = list(repositories)
        self.scope = scope or Scope(self.repositories)
        self._pulls: list[Issue] | None = None
        self._reviews = False  # whether the reviews of the pull requests are loaded

    @property
    def version(self) -> str:
        """What the results depend on, as a short hash: the repositories and their updates."""
        parts = sorted(
            (
                repository.pk,
                repository.updated,
                repository.issues_changed,
                repository.reviews_changed,
                repository.data_version,
                repository.error_at,
            )
            for repository in self.repositories
        )
        scope = sorted(repository.pk for repository in self.scope.repositories)
        return hashlib.sha256(repr((parts, scope)).encode()).hexdigest()[:20]

    def query(self):  # noqa: ANN201 - a QuerySet of Issue
        """The pull requests, the newest first, as the table shows them."""
        return Issue.objects.filter(repository__in=self.repositories, pull_request=True).order_by(
            "-created", "-pk"
        )

    def ids(self) -> list[int]:
        """The ids of all pull requests, the newest first."""
        key = f"pull-ids:{self.version}"
        found = cache.get(key)
        if found is None:
            found = list(self.query().values_list("pk", flat=True))
            cache.set(key, found, CACHED_SECONDS)
        return found

    def pulls(self, reviews: bool = True) -> list[Issue]:
        """All pull requests with what the conditions read, loaded once.

        Parameters:
            reviews: Whether the reviews of each are needed too, loaded when first needed.

        Returns:
            The pull requests, the newest first.
        """
        if self._pulls is None:
            self._pulls = list(
                self.query()
                .select_related("author", "repository", "pull_state")
                .prefetch_related("labels")
            )
        if reviews and not self._reviews:
            prefetch_related_objects(self._pulls, "reviews")
            self._reviews = True
        return self._pulls

    def of(self, column: Column) -> dict[int, bool | None]:
        """Whether a column applies to each pull request.

        Parameters:
            column: The column.

        Returns:
            The result by the id of the pull request: True, False, or None while not known.
        """
        name = hashlib.sha256(column.encode().encode()).hexdigest()[:20]  # no spaces in keys
        key = f"column:{self.version}:{name}"
        found = cache.get(key)
        if found is None:
            pulls = self.pulls(reviews=column.group.id == "reviews")
            found = {pull.pk: column.applies(pull, self.scope) for pull in pulls}
            cache.set(key, found, CACHED_SECONDS)
        return found

    def matching(self, columns: list[Column]) -> list[int]:
        """The pull requests that the columns show, the newest first.

        The filters are an OR: a pull request is shown when any column that filters (one that
        shows only the pull requests it applies to, or only those it does not apply to) shows
        it. Columns that show both do not filter; without columns that filter, all are shown.

        Parameters:
            columns: The columns of conditions.

        Returns:
            The ids of the pull requests.
        """
        filtering = [column for column in columns if column.filter != "all"]
        ids = self.ids()
        if not filtering:
            return ids
        results = [(column, self.of(column)) for column in filtering]
        return [pk for pk in ids if any(c.shows(found.get(pk)) for c, found in results)]

    def count(self, column: Column) -> int:
        """How many pull requests a column applies to.

        Parameters:
            column: The column.

        Returns:
            The number.
        """
        return sum(result is True for result in self.of(column).values())

    def rows(self, ids: list[int], columns: list[Column]) -> list[dict]:
        """The rows of a page of the table: the pull requests with the cells of the columns.

        Parameters:
            ids: The pull requests of the page, in their order.
            columns: The columns of conditions.

        Returns:
            Each pull request with ``cells``: the column, whether it applies, the parts of the
            cell, and why it is not known.
        """
        related = ["labels"] + (
            ["reviews"] if any(c.group.id == "reviews" for c in columns) else []
        )
        loaded = {
            pull.pk: pull
            for pull in Issue.objects.filter(pk__in=ids)
            .select_related("author", "repository", "pull_state")
            .prefetch_related(*related)
        }
        results = [self.of(column) for column in columns]
        rows = []
        for pk in ids:
            pull = loaded.get(pk)
            if pull is None:  # removed since
                continue
            cells = []
            for column, found in zip(columns, results, strict=True):
                result = found.get(pk)
                cells.append(
                    {
                        "column": column,
                        "result": result,
                        "parts": column.group.cell(pull, column.choices, self.scope),
                        "reason": column.group.unknown(pull, column.choices)
                        if result is None
                        else "",
                    }
                )
            rows.append({"pull": pull, "cells": cells})
        return rows
