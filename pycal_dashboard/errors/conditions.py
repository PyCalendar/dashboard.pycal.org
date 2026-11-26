"""Errors of the conditions that are checked on pull requests: their names and inputs."""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class ConditionError(DashboardError):
    """A condition could not be configured or checked.

    Resolve:
        Check the name and the inputs of the condition on its page of the documentation, see
        :doc:`/reference/conditions/index`.
    """

    title = _("The condition could not be configured")
    guide = "reference/conditions/index.html"
    guide_title = _("Conditions")


class UnknownCondition(ConditionError):
    """There is no condition with this id.

    This happens when:

    - the configuration of a condition names an id that does not exist, or
    - the table of pull requests is asked for a column of a kind that does not exist, in its
      address or in its menu.

    Resolve:
        - For a condition, use one of the ids of :doc:`/reference/conditions/index`, such as
          ``label_exists``.
        - For a column, reload the table of pull requests and choose the column in its menu.

    Note:
        The detail is the id that is not known.
    """

    title = _("Unknown condition")


class ConditionInputMissing(ConditionError):
    """A condition needs an input that its configuration does not have.

    This happens when:

    - the configuration of a condition leaves out an input that is required, or
    - a column of the table of pull requests is chosen without a value it needs, such as the
      name of a label, a number, a text, or at least one switch that is on.

    Resolve:
        - For a condition, give every input that the page of the condition lists as required.
        - For a column, fill in its fields or switch on one of its switches, and choose it
          again.

    Note:
        The detail names the condition or the column and the missing input, such as
        ``labels: label``.
    """

    title = _("An input of the condition is missing")


class ConditionInputUnknown(ConditionError):
    """The configuration of a condition has an input that the condition does not know.

    This happens when:

    - the configuration has an input whose name the condition does not have,
    - an input has a value that is none of its choices, such as a comparison or a kind of
      review, or
    - a menu of the table of pull requests names a column or a filter that the table does
      not have.

    Resolve:
        - When the name of an input is wrong, remove the input, or check its name on the page
          of the condition.
        - When a value is wrong, give one of the choices that the page of the condition lists.
        - When it happens in the table of pull requests, reload the table and choose again.

    Note:
        The detail names the input and the value that is not known, or the fields of the form.
    """

    title = _("Unknown input of the condition")


class ConditionInputNotText(ConditionError):
    """An input of a condition that needs a text got no text, an empty one or one too long.

    Resolve:
        Give it as a text that is not empty, such as ``"needs review"``, with at most as many
        characters as the input allows: 200, or 100 for the name of a label and for a text to
        match.

    Note:
        The detail names the input and the value that was given.
    """

    title = _("The input is not a text")


class ConditionInputNotBoolean(ConditionError):
    """An input of a condition that is on or off got a value that is neither.

    Resolve:
        Give it as ``true`` or ``false``.

    Context:
        A form sends ``on`` for a switch that is on. The input also takes ``1`` and ``yes``
        for on, and ``0``, ``no`` and an empty text for off.

    Note:
        The detail names the input and the value that was given.
    """

    title = _("The input is neither on nor off")


class ConditionInputNotInteger(ConditionError):
    """An input of a condition that is a whole number got a value that is none.

    Resolve:
        Give it as a number without a fraction, such as ``3``.

    Note:
        The detail names the input and the value that was given.
    """

    title = _("The input is not a whole number")


class ConditionInputNotNumber(ConditionError):
    """An input of a condition that is a number got a value that is no finite number.

    Resolve:
        Give it as a number, with a point before a fraction, such as ``1.5`` or ``2``.

    Note:
        The detail names the input and the value that was given.
    """

    title = _("The input is not a number")


class ConditionInputOutOfRange(ConditionError):
    """A number given to a condition is smaller or larger than it allows.

    Resolve:
        Give a number from the smallest to the largest number of the input, as the page of the
        condition says them; a positive number starts at 1.

    Note:
        The detail names the input, the number, and the smallest and the largest number of the
        input; ``None`` is no limit.
    """

    title = _("The number is out of range")


class ConditionRangeInvalid(ConditionError):
    """A range given to a condition is not two whole numbers, the first not above the second.

    Resolve:
        Give it as ``[low, high]``, such as ``[1, 5]``.

    Context:
        A form gives it as a text with one hyphen, such as ``1-5``.

    Note:
        The detail names the input and the range that was given.
    """

    title = _("Invalid range")


class TextPatternInvalid(ConditionError):
    r"""A text to match is empty or too long, or a regular expression is wrong or may be slow.

    Resolve:
        - Give a text of 1 to 100 characters.
        - For a regular expression, give one that is valid for Python, such as ``^(fix|feat):``,
          without repetitions of groups that repeat themselves, such as ``(a+)+``, and without
          back-references, such as ``\1``.

    Context:
        Repetitions of groups that repeat themselves and back-references are refused, as they
        can take very long to match.

    Note:
        The detail says what is wrong, such as ``may be slow: (a+)+b``.
    """

    title = _("The text to match is not valid")


class ConditionLabelUnknown(ConditionError):
    """The repository has no label of this name.

    Resolve:
        - Use the name of a label of the repository, as GitHub shows it on its page of labels.
        - When you just created the label on GitHub, press *Update* on the page of the project,
          wait for the update, and try again.

    Context:
        The dashboard knows the labels of a repository after its update.

    Note:
        The detail names the repository and the label, such as ``owner/repository: bug``.
    """

    title = _("Unknown label")


class ConditionNotInGroup(ConditionError):
    """A column cannot show a condition, as its group has no choices for it.

    This happens when a condition, or its NOT, is put into a column of a group of other
    conditions, such as a condition of reviews into a column of labels.

    Resolve:
        When it happens in the table of pull requests, reload the table and choose the column
        in its menu again.

    Context:
        Each column of the table of pull requests writes its condition into the address with
        the choices of its group (:doc:`/reference/conditions/index`).

    Note:
        The detail names the group and the condition, such as ``labels: reviews``.
    """

    title = _("The column cannot show the condition")
