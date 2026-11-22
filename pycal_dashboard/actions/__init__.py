"""The actions of the site and the log of why they happened.

Every effect of the site, such as the rights of an administrator, is an :class:`Action`: it
does the effect and records itself, with its reason, in the current :class:`Trigger`, such as
the webhook or the person that caused it. The administrators read the log on ``/logs/``.
"""

from .action import Action
from .admin_rights_changed import AdminRightsChanged
from .email_sent import EmailSent
from .image_hosts_saved import ImageHostsSaved
from .label_added import LabelAdded
from .label_removed import LabelRemoved
from .message_written import MessageWritten
from .preferences_saved import PreferencesSaved
from .settings_saved import SettingsSaved
from .step_label_deleted import StepLabelDeleted
from .step_label_saved import StepLabelSaved
from .trigger import Trigger
from .webhook_trigger import WebhookTrigger

__all__ = [
    "ImageHostsSaved",
    "Action",
    "AdminRightsChanged",
    "EmailSent",
    "LabelAdded",
    "LabelRemoved",
    "MessageWritten",
    "PreferencesSaved",
    "SettingsSaved",
    "StepLabelDeleted",
    "StepLabelSaved",
    "Trigger",
    "WebhookTrigger",
]
