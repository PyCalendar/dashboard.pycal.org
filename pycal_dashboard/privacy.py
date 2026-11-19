"""The privacy policy: which data of people the site keeps, and who gets which of it.

The page *Privacy* (``/about/privacy/``) shows these lists. They must say the truth at every
version: ``tests/test_privacy.py`` fails when a model or a field is added without being listed
in :data:`MODELS`, and when a page loads anything from another site than those of
:data:`EXTERNAL_HOSTS`.
"""

from django.utils.translation import gettext_lazy as _

# The data that the site keeps of people: what, whose, who sees it, and why.
DATA = {
    "account": {
        "what": _(
            "Your account on GitHub as GitHub describes it when you sign in: your GitHub name "
            "and id, your name, your avatar and the other public details of your profile; "
            "your verified email addresses; the time you signed in."
        ),
        "whose": _("People who sign in"),
        "seen_by": _("You and the people who run the site"),
        "why": _("To know who you are, and to send you the emails you choose."),
    },
    "token": {
        "what": _(
            "The token that GitHub gives the site when you sign in, with the scopes user:email "
            "and read:org."
        ),
        "whose": _("People who sign in"),
        "seen_by": _("Nobody: the site uses it for you"),
        "why": _(
            "To list your organizations and the repositories you may add to a project, and to "
            "check that you may read a private repository."
        ),
    },
    "preferences": {
        "what": _("Your language, your colors and the emails you want."),
        "whose": _("People who sign in"),
        "seen_by": _("You and the people who run the site"),
        "why": _("To show the site as you like on every device."),
    },
    "projects": {
        "what": _(
            "The projects you create, and the role of each collaborator with their GitHub name."
        ),
        "whose": _("Collaborators of projects"),
        "seen_by": _(
            "Everybody sees public projects; only the collaborators see who the collaborators "
            "are, and the private projects."
        ),
        "why": _("To show the projects and to decide who may change them."),
    },
    "github": {
        "what": _(
            "The issues and pull requests of the repositories of the projects: their title, "
            "description and times, and who created them with their GitHub name, id, name and "
            "the address of their avatar."
        ),
        "whose": _("People on GitHub, also those who never use this site"),
        "seen_by": _(
            "Everybody, for public repositories, as on GitHub; for private repositories, only "
            "the collaborators of their private projects."
        ),
        "why": _("To show the work of the community together."),
    },
    "installations": {
        "what": _(
            "The installations of the GitHub App: the account, its permissions, and the GitHub "
            "ids of the people who installed or changed it."
        ),
        "whose": _("People who install the GitHub App"),
        "seen_by": _("The people who run the site"),
        "why": _("To email them when the app needs more permissions."),
    },
    "log": {
        "what": _(
            "The log of the site and the webhooks GitHub sent: what happened, when, and the "
            "GitHub name of who caused it."
        ),
        "whose": _("People who sign in or act on the repositories"),
        "seen_by": _("The people who run the site"),
        "why": _("To find and solve errors."),
    },
    "requests": {
        "what": _(
            "Every request in the log of the server: the address it came from, the time, the "
            "page and the browser."
        ),
        "whose": _("Everybody who visits the site"),
        "seen_by": _("The people who run the site and its server"),
        "why": _("To keep the site running and safe."),
    },
}

# Every model of the site and of the packages it keeps data in, with the entry of DATA that
# describes it and all its fields; None for models without data of people, with their fields
# too, so that a new field is looked at. tests/test_privacy.py compares them to the models.
MODELS = {
    "pycal_dashboard.Profile": ("account", {"id", "user", "github_name", "github_id"}),
    "pycal_dashboard.GitHubUser": (
        "github",
        {"id", "github_id", "login", "name", "avatar_url", "type", "user"},
    ),
    "pycal_dashboard.Preferences": (
        "preferences",
        {"id", "user", "language", "theme", "email_permissions"},
    ),
    "pycal_dashboard.Project": (
        "projects",
        {"id", "slug", "name", "description", "public", "created_by", "created", "updated"},
    ),
    "pycal_dashboard.ProjectMember": ("projects", {"id", "project", "user", "role", "added"}),
    "pycal_dashboard.ProjectSlug": (None, {"id", "slug", "project", "since", "until"}),
    "pycal_dashboard.Issue": (
        "github",
        {
            "id",
            "repository",
            "number",
            "github_id",
            "pull_request",
            "title",
            "author",
            "description",
            "state",
            "created",
            "closed",
            "merged",
            "changed",
        },
    ),
    "pycal_dashboard.Label": (
        None,
        {"id", "repository", "github_id", "name", "description", "color"},
    ),
    "pycal_dashboard.PullRequestState": (
        None,
        {
            "id",
            "issue",
            "head_sha",
            "head_ref",
            "base_ref",
            "mergeable",
            "mergeable_state",
            "auto_merge",
            "checks",
            "updated",
            "checks_updated",
        },
    ),
    "pycal_dashboard.Repository": (
        None,
        {
            "id",
            "full_name",
            "github_id",
            "private",
            "description",
            "installation",
            "open_issues",
            "open_pull_requests",
            "updated",
            "error_code",
            "error_detail",
            "error_at",
            "data_version",
            "issues_changed",
            "created",
        },
    ),
    "pycal_dashboard.Installation": (
        "installations",
        {
            "id",
            "github_id",
            "account_login",
            "account_type",
            "permissions",
            "events",
            "admin_github_ids",
            "permissions_notified",
            "suspended",
            "removed",
            "created",
            "updated",
        },
    ),
    "pycal_dashboard.UpdateJob": (
        "projects",
        {
            "id",
            "project",
            "repository",
            "requested_by",
            "status",
            "done",
            "total",
            "errors",
            "created",
            "started",
            "finished",
        },
    ),
    "pycal_dashboard.LogTrigger": (
        "log",
        {"id", "kind", "summary", "created", "actor_login", "repository", "delivery"},
    ),
    "pycal_dashboard.LogAction": ("log", {"id", "trigger", "kind", "text", "created"}),
    "pycal_dashboard.WebhookDelivery": (
        "log",
        {
            "id",
            "delivery",
            "event",
            "action",
            "repository",
            "received",
            "outcome",
            "error",
            "detail",
        },
    ),
    "auth.User": (
        "account",
        {
            "id",
            "password",
            "last_login",
            "is_superuser",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_active",
            "date_joined",
        },
    ),
    "socialaccount.SocialAccount": (
        "account",
        {"id", "user", "provider", "uid", "last_login", "date_joined", "extra_data"},
    ),
    "socialaccount.SocialToken": (
        "token",
        {"id", "app", "account", "token", "token_secret", "expires_at"},
    ),
    "account.EmailAddress": ("account", {"id", "user", "email", "verified", "primary"}),
}

# Who else gets data of people, and which.
PARTIES = [
    {
        "name": _("GitHub"),
        "gets": _(
            "When you sign in, GitHub tells the site who you are; the site asks GitHub for "
            "repositories, issues and pull requests with your token or that of the GitHub App. "
            "Your browser loads the avatars of people from GitHub "
            "(avatars.githubusercontent.com), which sees the address of your browser, but not "
            "the page: the site sends no referrer. Links to GitHub lead there."
        ),
        "policy": "https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement",
    },
    {
        "name": _("The mail server of the site"),
        "gets": _(
            "Your email address and the text of each email the site sends you, such as the "
            "notice that an installation needs more permissions."
        ),
        "policy": "",
    },
    {
        "name": _("The server and the people who run the site"),
        "gets": _(
            "Everything the site keeps: they run the server and see the Django admin, the log "
            "and the webhooks GitHub sent."
        ),
        "policy": "",
    },
]

# The hosts of other sites that the pages load anything from, such as images. Nothing else
# comes from other sites: no fonts, scripts or styles. tests/test_privacy.py checks it.
EXTERNAL_HOSTS = {"avatars.githubusercontent.com"}

# The cookies of the site; it has no others, also none of other sites.
COOKIES = [
    ("sessionid", _("Keeps you signed in.")),
    ("csrftoken", _("Protects the forms against other sites.")),
    ("django_language", _("The language you chose.")),
    ("theme", _("The colors you chose.")),
]
