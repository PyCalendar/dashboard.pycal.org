"""The actions of the site and the log of why they happened.

Every effect of the site, such as the rights of an administrator, is an :class:`Action`: it
does the effect and records itself, with its reason, in the current :class:`Trigger`, such as
the webhook or the person that caused it. The administrators read the log on ``/logs/``.
"""

from .action import Action
from .admin_rights_changed import AdminRightsChanged
from .email_sent import EmailSent
from .label_added import LabelAdded
from .preferences_saved import PreferencesSaved
from .settings_saved import SettingsSaved
from .trigger import Trigger
from .webhook_trigger import WebhookTrigger

__all__ = [
    "Action",
    "AdminRightsChanged",
    "EmailSent",
    "LabelAdded",
    "PreferencesSaved",
    "SettingsSaved",
    "Trigger",
    "WebhookTrigger",
]
