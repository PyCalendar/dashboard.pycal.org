"""``makemessages`` without guessed translations: a new or changed text waits for its own."""

from django.core.management.commands.makemessages import Command as MakeMessages


class Command(MakeMessages):
    """``manage.py makemessages`` of Django, without fuzzy matching.

    A guessed (fuzzy) translation of a changed text is never shown, and the people decide when
    to translate: until then the text has no translation and shows in English.
    """

    msgmerge_options = [*MakeMessages.msgmerge_options, "--no-fuzzy-matching"]
