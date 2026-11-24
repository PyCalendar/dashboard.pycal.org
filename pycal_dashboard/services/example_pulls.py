"""Pull requests of a project as examples of how far they came, to review the message with."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycal_dashboard.conditions.group.column import Column
from pycal_dashboard.models import Issue

if TYPE_CHECKING:
    from pycal_dashboard.models import Project
    from pycal_dashboard.services.column_results import ColumnResults


class ExamplePulls:
    """One pull request for each state of the steps, from no quality check done to all of them.

    A pull request has done the tasks of the steps it went through and those done of the step
    it is in; outside of the steps, all of them. Each example differs from all others in its
    step or in the state of a task, see :meth:`examples`. The page of the message shows them
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
            [c for c in (Column.decode(v) for v in step.filter.columns) if c.checks]
            for step in project.steps.select_related("filter")
        ]
        self.total = sum(len(columns) for columns in self.steps)
        self.names = [step.name for step in project.steps.all()]

    def states(self) -> dict[int, tuple[int, int, tuple[str, ...]]]:
        """Where each pull request is: its tasks done, its step and the state of each task.

        Returns:
            By the id of the pull request: how many tasks it has done, the place of the step
            it is in (the number of steps when it is in none), and whether each task of the
            steps up to it is ``done``, ``todo`` or ``unknown``.
        """
        cells = [[(c, self.results.of(c)) for c in columns] for columns in self.steps]
        found = {}
        for pk in self.results.ids():
            done, place, states = 0, len(cells), []
            for index, columns in enumerate(cells):
                todo = 0
                for column, results in columns:
                    result = results.get(pk)
                    if column.shows(result):
                        todo += 1
                        states.append("todo")
                    else:
                        states.append("unknown" if result is None else "done")
                done += len(columns) - todo
                if todo:  # the step it is in: the steps after it do not count
                    place = index
                    break
            found[pk] = (done, place, tuple(states))
        return found

    def examples(self) -> list[dict]:
        """The examples: each in another state, from no quality check done to all of them.

        Two pull requests are in the same state when they are in the same step with the same
        tasks done, to do and not known; of them, the newest open one is the example, else
        the newest. The examples are ordered by the tasks done, then by their step.

        Returns:
            Each with the id of the pull request (``pk``), ``done``, ``total`` and the
            ``step`` it is in ("" for none); none without steps or pull requests.
        """
        if not self.steps:
            return []
        states = self.states()
        open_ids = set(
            Issue.objects.filter(pk__in=list(states), state=Issue.OPEN).values_list("pk", flat=True)
        )
        chosen: dict[tuple, int] = {}
        for pk in self.results.ids():  # the newest first
            state = states[pk]
            if state not in chosen or (pk in open_ids and chosen[state] not in open_ids):
                chosen[state] = pk
        return [
            {
                "pk": chosen[state],
                "done": state[0],
                "total": self.total,
                "step": self.names[state[1]] if state[1] < len(self.names) else "",
            }
            for state in sorted(chosen)
        ]
