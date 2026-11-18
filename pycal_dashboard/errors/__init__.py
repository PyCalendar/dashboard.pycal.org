"""The errors people can meet, each with what it means and how to solve it, grouped by topic.

The site shows an error with its title, the detail and a link to its description in the
documentation (``DashboardError.docs_url``).
"""

from .account import (
    AccountError,
    NoGitHubAccount,
)
from .base import (
    DashboardError,
    UnexpectedError,
)
from .configuration import (
    ConfigurationError,
    FaviconNotFound,
    InvalidColor,
    InvalidFooterLink,
    InvalidOrganizationSetting,
    UnknownColor,
    UnsupportedFavicon,
)
from .dashboard import (
    ApiEndpointNotFound,
    InvalidInstallationId,
    LookupFailed,
)
from .github import (
    GitHubError,
    GitHubLoginExpired,
    GitHubNotFound,
    GitHubRateLimited,
    GitHubUnreachable,
    MissingPermissions,
    SignInNotConfigured,
)
from .registration import (
    AppAlreadyRegistered,
    AppSettingsInEnvironment,
    InvalidAppName,
    InvalidOrganization,
    ManifestConversionFailed,
    PrivateKeyFileExists,
    RegistrationCodeMissing,
    RegistrationError,
    RegistrationExpired,
    RegistrationNotSaved,
    SetupCodeWrong,
)
from .translate import all_errors, translate
from .webhooks import (
    WebhookError,
    WebhookEventMissing,
    WebhookPayloadInvalid,
    WebhookSecretNotConfigured,
    WebhookSignatureInvalid,
    WebhookSignatureMissing,
)

__all__ = [
    "AccountError",
    "ApiEndpointNotFound",
    "AppAlreadyRegistered",
    "AppSettingsInEnvironment",
    "ConfigurationError",
    "DashboardError",
    "FaviconNotFound",
    "GitHubError",
    "GitHubLoginExpired",
    "GitHubNotFound",
    "GitHubRateLimited",
    "GitHubUnreachable",
    "InvalidAppName",
    "InvalidColor",
    "InvalidFooterLink",
    "InvalidInstallationId",
    "InvalidOrganization",
    "InvalidOrganizationSetting",
    "LookupFailed",
    "ManifestConversionFailed",
    "MissingPermissions",
    "NoGitHubAccount",
    "PrivateKeyFileExists",
    "RegistrationCodeMissing",
    "RegistrationError",
    "RegistrationExpired",
    "RegistrationNotSaved",
    "SetupCodeWrong",
    "SignInNotConfigured",
    "UnexpectedError",
    "UnknownColor",
    "UnsupportedFavicon",
    "WebhookError",
    "WebhookEventMissing",
    "WebhookPayloadInvalid",
    "WebhookSecretNotConfigured",
    "WebhookSignatureInvalid",
    "WebhookSignatureMissing",
    "all_errors",
    "translate",
]
