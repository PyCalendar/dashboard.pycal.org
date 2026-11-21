"""Evidence of a condition: where people see on GitHub, or on the site, why it holds or not."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    """A link that shows why a condition holds for a pull request, or why it does not.

    The data specs give the evidence of their data (:meth:`DataSpec.evidence
    <pycal_dashboard.conditions.spec.base.DataSpec.evidence>`), such as the checks of a pull
    request on GitHub; a condition shows the least of it that decides it, such as two reviews
    of at least two (:meth:`Condition.evidence
    <pycal_dashboard.conditions.condition.base.Condition.evidence>`).

    Attributes:
        text: What the link shows, translated, such as *The checks on GitHub*.
        url: Where, such as ``https://github.com/PyCalendar/icalendar/pull/2188/checks``.
    """

    text: str
    url: str

    def data(self) -> dict:
        """The evidence for the JSON of the page of a pull request.

        Returns:
            Its ``text`` and ``url``.
        """
        return {"text": str(self.text), "url": self.url}

    @staticmethod
    def unique(found: list[Evidence]) -> list[Evidence]:
        """The evidence without links that came before, in its order.

        Parameters:
            found: The evidence, maybe with the same link more than once.

        Returns:
            Each link once.

        Examples:
            >>> a, b = Evidence("A", "https://a"), Evidence("B", "https://b")
            >>> [e.text for e in Evidence.unique([a, b, Evidence("C", "https://a")])]
            ['A', 'B']
        """
        seen: set[str] = set()
        unique = []
        for evidence in found:
            if evidence.url not in seen:
                seen.add(evidence.url)
                unique.append(evidence)
        return unique
