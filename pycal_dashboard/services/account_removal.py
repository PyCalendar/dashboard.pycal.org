"""Delete the account of a person, with what belongs only to them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Count, Q

from pycal_dashboard.actions import Trigger
from pycal_dashboard.errors import AccountDeletionNotConfirmed, AccountOwnsSharedProjects
from pycal_dashboard.models import Project, ProjectMember

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser


@dataclass(frozen=True)
class AccountRemoval:
    """What deleting an account deletes, and what stops it.

    Deleting an account deletes the user with its GitHub account, token, email addresses,
    preferences and roles in projects, and the projects that only this person has: those of
    which they are the only collaborator. A project that others share, of which they are the
    only owner, stops it: a project always has an owner. The issues and pull requests of
    GitHub stay, as on GitHub; the GitHub user is no longer linked to an account.

    Attributes:
        user: The person.
        login: Their GitHub name, which they type to confirm.
    """

    user: AbstractBaseUser
    login: str

    def own_projects(self) -> list[Project]:
        """The projects that are deleted with the account: only this person is in them.

        Returns:
            The projects.
        """
        mine = ProjectMember.objects.filter(user=self.user).values("project")
        counted = Project.objects.filter(pk__in=mine)  # all members counted, not only this one
        return list(
            counted.annotate(people=Count("members", distinct=True))
            .filter(people=1)
            .order_by("name")
        )

    def shared_projects(self) -> list[Project]:
        """The projects that others share and of which this person is the only owner.

        Returns:
            The projects that stop the deletion.
        """
        mine = ProjectMember.objects.filter(user=self.user, role=ProjectMember.OWNER)
        owned = Project.objects.filter(pk__in=mine.values("project")).annotate(
            owners=Count("members", filter=Q(members__role=ProjectMember.OWNER), distinct=True),
            people=Count("members", distinct=True),
        )
        return list(owned.filter(owners=1, people__gt=1).order_by("name"))

    @transaction.atomic
    def delete(self, confirmation: str) -> list[str]:
        """Delete the account and the projects that only this person has.

        Parameters:
            confirmation: The GitHub name that the person typed; its case does not matter.

        Returns:
            The names of the deleted projects.

        Raises:
            AccountDeletionNotConfirmed: The typed name is not their GitHub name.
            AccountOwnsSharedProjects: They are the only owner of projects that others share.
        """
        if confirmation.strip().removeprefix("@").lower() != self.login.lower():
            raise AccountDeletionNotConfirmed(confirmation)
        shared = self.shared_projects()
        if shared:
            raise AccountOwnsSharedProjects(", ".join(project.slug for project in shared))
        projects = self.own_projects()
        names = [project.name for project in projects]
        with Trigger.start(
            "account", f"@{self.login} deleted their account", actor_login=self.login
        ):
            for project in projects:
                project.delete()
            self.user.delete()
        return names
