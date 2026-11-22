"""A change that restoring a backup makes in a project, such as adding or deleting a filter."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RestoreChange:
    """One change of :class:`~pycal_dashboard.services.restore_plan.RestorePlan`.

    Attributes:
        key: What it changes, such as ``filter-delete:Review``: the value of its checkbox.
        text: What it does, for people, such as *Delete the filter Review*.
        confirm: Whether it deletes or replaces something: it is made only when the person
            ticks its checkbox. Changes that only add are made without.
        note: Whether it is only said, such as a person who never signed in: nothing is made.
    """

    key: str
    text: str
    confirm: bool = False
    note: bool = False
