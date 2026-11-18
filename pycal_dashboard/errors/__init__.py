"""The errors people can meet, each with what it means and how to solve it, grouped by topic.

The site shows an error with its title, the detail and a link to its description in the
documentation (``DashboardError.docs_url``).
"""

from .account import (
    AccountError,
    NoGitHubAccount,
    UnknownPreference,
    WatchedRepositoryUnknown,
)
from .base import (
    DashboardError,
    UnexpectedError,
)
from .configuration import (
    ConfigurationError,
    InvalidColor,
    InvalidOrganizationSetting,
    UnknownColor,
    UnknownLabelRule,
)
from .dashboard import (
    ApiEndpointNotFound,
    ContributorNotFound,
    InvalidDays,
    InvalidFilter,
    InvalidPageNumber,
    LookupFailed,
    RepositoryNotFound,
)
from .github import (
    GitHubAnswerNotJSON,
    GitHubAppNotConfigured,
    GitHubError,
    GitHubLoginExpired,
    GitHubNotFound,
    GitHubRateLimited,
    GitHubUnreachable,
    InstallationNotAllowed,
    InstallationNotFound,
    InvalidPrivateKey,
    MissingPermissions,
    SignInNotConfigured,
)
from .labels import (
    CannotWriteLabels,
    LabelError,
    PullRequestSizeUnknown,
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
    WebhookPayloadIncomplete,
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
    "CannotWriteLabels",
    "ConfigurationError",
    "ContributorNotFound",
    "DashboardError",
    "GitHubAnswerNotJSON",
    "GitHubAppNotConfigured",
    "GitHubError",
    "GitHubLoginExpired",
    "GitHubNotFound",
    "GitHubRateLimited",
    "GitHubUnreachable",
    "InstallationNotAllowed",
    "InstallationNotFound",
    "InvalidAppName",
    "InvalidColor",
    "InvalidDays",
    "InvalidFilter",
    "InvalidOrganization",
    "InvalidOrganizationSetting",
    "InvalidPageNumber",
    "InvalidPrivateKey",
    "LabelError",
    "LookupFailed",
    "ManifestConversionFailed",
    "MissingPermissions",
    "NoGitHubAccount",
    "PrivateKeyFileExists",
    "PullRequestSizeUnknown",
    "RegistrationCodeMissing",
    "RegistrationError",
    "RegistrationExpired",
    "RegistrationNotSaved",
    "RepositoryNotFound",
    "SetupCodeWrong",
    "SignInNotConfigured",
    "UnexpectedError",
    "UnknownColor",
    "UnknownLabelRule",
    "UnknownPreference",
    "WatchedRepositoryUnknown",
    "WebhookError",
    "WebhookEventMissing",
    "WebhookPayloadIncomplete",
    "WebhookPayloadInvalid",
    "WebhookSecretNotConfigured",
    "WebhookSignatureInvalid",
    "WebhookSignatureMissing",
    "all_errors",
    "translate",
]
