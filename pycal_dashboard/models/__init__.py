"""The models of the dashboard, one per module.

The site keeps no data of GitHub, except its installations and their permissions.
"""

from .installation import Installation
from .log_action import LogAction
from .log_trigger import LogTrigger
from .preferences import Preferences
from .webhook_delivery import WebhookDelivery

__all__ = ["Installation", "LogAction", "LogTrigger", "Preferences", "WebhookDelivery"]
