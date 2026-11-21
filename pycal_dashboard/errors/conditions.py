"""Errors of the conditions that are checked on pull requests: their names and inputs."""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class ConditionError(DashboardError):
    """A condition could not be configured or checked.

    Check its name and inputs on its page of the documentation, see
    :doc:`/reference/conditions/index`.
    """

    title = _("The condition could not be configured")
    guide = "reference/conditions/index.html"
    guide_title = _("Conditions")


class UnknownCondition(ConditionError):
    """There is no condition with this id.

    Use one of the ids of :doc:`/reference/conditions/index`, such as ``label_exists``.
    """

    title = _("Unknown condition")


class ConditionInputMissing(ConditionError):
    """A condition needs an input that its configuration does not have.

    Give every input that the page of the condition lists as required.
    """

    title = _("An input of the condition is missing")


class ConditionInputUnknown(ConditionError):
    """The configuration of a condition has an input that the condition does not know.

    Remove it, or check its name on the page of the condition.
    """

    title = _("Unknown input of the condition")


class ConditionInputNotText(ConditionError):
    """An input of a condition must be a text.

    Give it as a text, such as ``"needs review"``.
    """

    title = _("The input is not a text")


class ConditionInputNotBoolean(ConditionError):
    """An input of a condition must be on or off.

    Give it as ``true`` or ``false``; a form sends ``on`` for a switch that is on.
    """

    title = _("The input is neither on nor off")


class ConditionInputNotInteger(ConditionError):
    """An input of a condition must be a whole number.

    Give it as a number without a fraction, such as ``3``.
    """

    title = _("The input is not a whole number")


class ConditionInputNotNumber(ConditionError):
    """An input of a condition must be a number.

    Give it as a number, with a point before a fraction, such as ``1.5`` or ``2``.
    """

    title = _("The input is not a number")


class ConditionInputOutOfRange(ConditionError):
    """A number given to a condition is smaller or larger than it allows.

    The page of the condition says the smallest and the largest number of the input; a positive
    number starts at 1.
    """

    title = _("The number is out of range")


class ConditionRangeInvalid(ConditionError):
    """A range given to a condition is not two whole numbers, the first not above the second.

    Give it as ``[low, high]``, such as ``[1, 5]``.
    """

    title = _("Invalid range")


class ConditionLabelUnknown(ConditionError):
    """The repository has no label of this name.

    Use the name of a label of the repository, as GitHub shows it on its page of labels; the
    site knows the labels after the update of the repository.
    """

    title = _("Unknown label")
