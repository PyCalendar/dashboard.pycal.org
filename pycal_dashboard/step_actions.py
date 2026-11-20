"""The actions of a step: labels added and removed when a pull request enters or completes it.

A step keeps them in ``PullRequestStep.actions`` as::

    {"enter": {"add": ["triage"], "remove": []},
     "complete": {"add": ["reviewed"], "remove": ["needs review"]}}

Steps saved before kept a list of labels to add on completing, such as
``[{"kind": "add_label", "label": "reviewed"}]``; :func:`normalized` reads both.
"""

from __future__ import annotations

# when the actions run: a pull request enters the step, or completes it (leaves it, done)
TRIGGERS = ("enter", "complete")
KINDS = ("add", "remove")
MAX_LABEL = 100  # the longest name of a label on GitHub


def normalized(actions: dict | list | None) -> dict[str, dict[str, list[str]]]:
    """The actions of a step in the current form.

    Parameters:
        actions: As the step keeps them; the list of before; None for none.

    Returns:
        For each trigger, the labels to ``add`` and to ``remove``.

    Examples:
        >>> normalized([{"kind": "add_label", "label": "done"}])["complete"]["add"]
        ['done']
        >>> normalized(None)["enter"]
        {'add': [], 'remove': []}
    """
    found = {trigger: {kind: [] for kind in KINDS} for trigger in TRIGGERS}
    if isinstance(actions, list):  # saved before: labels added on completing
        found["complete"]["add"] = [
            str(action["label"]) for action in actions if action.get("label")
        ]
        return found
    for trigger in TRIGGERS:
        for kind in KINDS:
            found[trigger][kind] = [
                str(label) for label in (actions or {}).get(trigger, {}).get(kind, [])
            ]
    return found


def labels(text: str) -> list[str]:
    """The labels of a field: names separated by commas, each once, in their order.

    Parameters:
        text: Such as ``needs review, triage``.

    Returns:
        The names.

    Examples:
        >>> labels(" needs review, triage,, Triage ,")
        ['needs review', 'triage']
    """
    found: dict[str, str] = {}
    for part in text.split(","):
        name = " ".join(part.split())[:MAX_LABEL]
        if name:
            found.setdefault(name.lower(), name)
    return list(found.values())


def renamed(actions: dict | list | None, old: str, new: str) -> dict[str, dict[str, list[str]]]:
    """The actions with a label renamed on GitHub, in any case.

    Parameters:
        actions: As the step keeps them.
        old: The name before.
        new: The name now.

    Returns:
        The actions in the current form.

    Examples:
        >>> renamed({"enter": {"add": ["Bug"], "remove": []}}, "bug", "defect")["enter"]["add"]
        ['defect']
    """
    found = normalized(actions)
    for trigger in TRIGGERS:
        for kind in KINDS:
            found[trigger][kind] = [
                new if label.lower() == old.lower() else label for label in found[trigger][kind]
            ]
    return found
