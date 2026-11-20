"""Pull requests of a project as examples of how far they came, to review the message with."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.models import Issue

if TYPE_CHECKING:
    from pycal_dashboard.models import Project
    from pycal_dashboard.services.column_results import ColumnResults


class ExamplePulls:
    """One pull request for each number of tasks done, from none to all.

    A pull request has done the tasks of the steps it went through and those done of the step
    it is in; outside of the steps, all of them. Of the pull requests with the same number,
    the newest open one is the example, else the newest. The page of the message shows them
    one after the other, with one more task done each time, so that the message can be
    reviewed in every state. The results of the columns come from the cache
    (:class:`~pycal_dashboard.services.column_results.ColumnResults`).
    """

    def __init__(self, project: Project, results: ColumnResults):
        """The steps of a project and the results of their conditions.

        Parameters:
            project: The project.
            results: The results of the columns for the pull requests the person sees.
        """
        self.results = results
        self.steps = [
            [c for c in (Column.decode(v) for v in step.filter.columns) if c.filter != "all"]
            for step in project.steps.select_related("filter")
        ]
        self.total = sum(len(columns) for columns in self.steps)

    def done(self) -> dict[int, int]:
        """How many tasks each pull request has done.

        Returns:
            The number by the id of the pull request.
        """
        cells = [[(c, self.results.of(c)) for c in columns] for columns in self.steps]
        found = {}
        for pk in self.results.ids():
            done = 0
            for columns in cells:
                todo = sum(column.shows(results.get(pk)) for column, results in columns)
                done += len(columns) - todo
                if todo:  # the step it is in: the steps after it do not count
                    break
            found[pk] = done
        return found

    def examples(self) -> list[dict]:
        """The examples, from no task done to all of them.

        Returns:
            Each with the id of the pull request (``pk``), ``done`` and ``total``; none
            without steps or pull requests.
        """
        if not self.steps:
            return []
        done = self.done()
        open_ids = set(
            Issue.objects.filter(pk__in=list(done), state=Issue.OPEN).values_list("pk", flat=True)
        )
        chosen: dict[int, int] = {}
        for pk in self.results.ids():  # the newest first
            number = done[pk]
            if number not in chosen or (pk in open_ids and chosen[number] not in open_ids):
                chosen[number] = pk
        return [
            {"pk": chosen[number], "done": number, "total": self.total} for number in sorted(chosen)
        ]
