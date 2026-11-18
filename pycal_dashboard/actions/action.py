"""The base of the actions: do the effect, then record it in the log."""

from pycal_dashboard.models import LogAction

from .trigger import Trigger


class Action:
    """An effect of the site and its record in the log.

    Subclasses set ``kind``, describe themselves in :meth:`text` and do their effect in
    :meth:`perform`; :meth:`run` does both.
    """

    kind = "action"

    def text(self) -> str:
        """What was done and why, for people."""
        raise NotImplementedError

    def perform(self) -> None:
        """Do the effect; records without an effect do nothing."""

    def run(self) -> "Action":
        """Do the effect and record it in the current trigger.

        Returns:
            The action.
        """
        self.perform()
        LogAction.objects.create(trigger=Trigger.current(), kind=self.kind, text=self.text()[:500])
        return self
