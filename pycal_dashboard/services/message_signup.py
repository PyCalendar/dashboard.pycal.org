"""People sign up for the PR message of a project themselves: their GitHub handle in its authors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext

from pycal_dashboard.errors import MessageSignupClosed, MessageSignupWithoutHandle
from pycal_dashboard.models import PullRequestMessage
from pycal_dashboard.services.update_queue import UpdateQueue

if TYPE_CHECKING:
    from pycal_dashboard.services.project_access import ProjectAccess


class MessageSignup:
    """The page where a person signs up for the PR message of a project, for their pull requests.

    It is open while the project has an applied message whose scope has the open pull requests
    of people (``to_authors``). Signing up adds the GitHub handle of the person to the
    ``authors`` of the message, as the writers do on the page *Synchronization*; switching it
    off takes it out. Whoever sees the project may sign up, for their own pull requests only.

    Attributes:
        access: The rights of the person in the project.
    """

    def __init__(self, access: ProjectAccess):
        """The page of a project, for a person.

        Parameters:
            access: The rights of the person in the project.
        """
        self.access = access

    @staticmethod
    def default_text() -> str:
        """The text of the page for visitors, before signing in, unless the writers change it."""
        return gettext("Log in to enable the Pull Request Messages\non these repositories:")

    @property
    def message(self) -> PullRequestMessage | None:
        """The message that people sign up for; None when there is none or it is closed."""
        message = PullRequestMessage.objects.filter(project=self.access.project).first()
        if message is None or not message.template or not message.to_authors:
            return None
        return message

    def require_open(self) -> PullRequestMessage:
        """The message that people sign up for.

        Returns:
            The message.

        Raises:
            MessageSignupClosed: The project has no applied message for the pull requests of
                people.
        """
        message = self.message
        if message is None:
            raise MessageSignupClosed(self.access.project.name)
        return message

    def text(self) -> str:
        """The text of the page before signing in: that of the writers, else the default."""
        message = self.message
        return (message.signup_text if message else "") or self.default_text()

    @property
    def handle(self) -> str:
        """The GitHub handle of the person who signed in; empty without one."""
        profile = getattr(self.access.user, "profile", None)
        return (profile.github_name or "") if profile else ""

    @property
    def signed_up(self) -> bool:
        """Whether the person signed up: their GitHub handle is one of the authors."""
        message = self.message
        handle = self.handle.lower()
        return bool(message and handle) and handle in {a.lower() for a in message.authors}

    def repositories(self) -> list[str]:
        """The repositories of the project that the person sees, such as ``github.com/a/b``.

        Their pull requests get the message; the page shows them as text, without links.
        """
        repositories = self.access.project.repositories.order_by("full_name")
        if not self.access.is_member:  # a repository that became private: its people only
            repositories = repositories.filter(private=False)
        return [f"github.com/{repository.full_name}" for repository in repositories]

    def save(self, on: bool) -> bool:
        """Sign the person up, or take them out; their pull requests are updated in the background.

        Parameters:
            on: Whether their pull requests get the message.

        Returns:
            Whether it changed.

        Raises:
            MessageSignupClosed: The project has no applied message for the pull requests of
                people.
            MessageSignupWithoutHandle: The account of the person has no GitHub handle.
        """
        message = self.require_open()
        handle = self.handle
        if not handle:
            raise MessageSignupWithoutHandle(self.access.user.get_username())
        if on == self.signed_up:
            return False
        others = [a for a in message.authors if a.lower() != handle.lower()]
        message.authors = [*others, handle] if on else others
        message.save(update_fields=["authors", "updated"])
        UpdateQueue.add(self.access.project, self.access.user)  # the comments, in the background
        return True
