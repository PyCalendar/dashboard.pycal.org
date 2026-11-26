"""The results of the columns of conditions for all pull requests of a project, cached."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import TYPE_CHECKING

from django.core.cache import cache
from django.db.models import prefetch_related_objects

from pycal_dashboard.conditions.group.conjunction import Conjunction
from pycal_dashboard.conditions.results_version import RESULTS_VERSION
from pycal_dashboard.conditions.state.scope import Scope
from pycal_dashboard.models import Issue

if TYPE_CHECKING:
    from pycal_dashboard.conditions.group.column import Column
    from pycal_dashboard.models import Project, Repository

CACHED_SECONDS = 24 * 3600  # the key changes with every update of a repository


class ColumnResults:
    """Whether each column applies to each pull request of repositories, kept in the cache.

    A column is evaluated for all pull requests at once, with the data they need loaded in a
    few queries, and its results are kept in the cache of Django under the version of the
    repositories: when they were updated and read. An update of a repository makes a new
    version, so nothing is evaluated again until GitHub changed something. A page of the table
    then loads only the pull requests it shows (:meth:`rows`).
    """

    def __init__(
        self,
        repositories: list[Repository],
        scope: Scope | None = None,
        project: Project | None = None,
    ):
        """The pull requests of repositories.

        Parameters:
            repositories: The repositories that the person sees.
            scope: Where the states of the authors are counted; the repositories by default.
            project: The project, for the conditions on data of the dashboard; None for none.
        """
        self.repositories = list(repositories)
        self.scope = scope or Scope(self.repositories, project)
        self._pulls: list[Issue] | None = None
        self._reviews = False  # whether the reviews of the pull requests are loaded

    @property
    def version(self) -> str:
        """What the results depend on, as a short hash: the repositories and their updates.

        Also :data:`~pycal_dashboard.conditions.results_version.RESULTS_VERSION`, which changes
        with what the conditions compute.
        """
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
        return hashlib.sha256(repr((parts, scope, RESULTS_VERSION)).encode()).hexdigest()[:20]

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

    def of(self, column: Column | Conjunction) -> dict[int, bool | None]:
        """Whether a column applies to each pull request, or the conditions of an AND hold.

        Parameters:
            column: The column, or the AND of columns.

        Returns:
            The result by the id of the pull request: True, False, or None while not known.
        """
        if isinstance(column, Conjunction):
            return column.results([self.of(member) for member in column.in_force])
        key = self.key(column)
        found = cache.get(key) if column.group.cached else None
        if found is None:
            pulls = self.pulls(reviews=column.group.id == "reviews")
            found = {pull.pk: column.applies(pull, self.scope) for pull in pulls}
            if column.group.cached:
                cache.set(key, found, CACHED_SECONDS)
        return found

    def cached(self, column: Column | Conjunction) -> dict[int, bool | None] | None:
        """The results of a column if the cache has them, without evaluating it.

        A page of one pull request uses them where they are, and evaluates the column for
        that pull request alone where they are not, which is faster than for all.

        Parameters:
            column: The column, or the AND of columns: the cache has it when it has them all.

        Returns:
            The results by the id of the pull request; None when they are not in the cache.
        """
        if isinstance(column, Conjunction):
            found = [self.cached(member) for member in column.in_force]
            return None if any(f is None for f in found) else column.results(found)
        if not column.group.cached:  # such as data of the dashboard: evaluated each time
            return None
        return cache.get(self.key(column))

    def key(self, column: Column) -> str:
        """The key of the results of a column in the cache, for the version of now.

        Parameters:
            column: The column.

        Returns:
            The key, without spaces.
        """
        # the same results, whether the column is joined with others by AND or not
        name = hashlib.sha256(replace(column, joined=0).encode().encode()).hexdigest()[:20]
        return f"column:{self.version}:{name}"

    def matching(self, columns: list[Column]) -> list[int]:
        """The pull requests that the columns show, the newest first.

        The filters are an OR: a pull request is shown when any column that filters (one that
        shows only the pull requests it applies to, or only those it does not apply to) shows
        it. Columns that show both do not filter; without columns that filter, all are shown.
        Of those, a pull request that a condition of Skip if applies to is not shown. Columns
        joined by AND are one condition (:class:`Conjunction`): it shows a pull request when
        all of them show it, and skips when all of them apply.

        Parameters:
            columns: The columns of conditions.

        Returns:
            The ids of the pull requests.
        """
        conditions = Conjunction.of(columns)
        filtering = [item for item in conditions if item.checks]
        skipping = [self.of(item) for item in conditions if item.skips]
        ids = self.ids()
        if filtering:
            results = [(column, self.of(column)) for column in filtering]
            ids = [pk for pk in ids if any(c.shows(found.get(pk)) for c, found in results)]
        return [pk for pk in ids if not any(found.get(pk) is True for found in skipping)]

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
