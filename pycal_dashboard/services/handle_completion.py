"""The GitHub handles that a field proposes while a person types: the same in every field."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.db.models import Q

from pycal_dashboard.models import GitHubUser, Profile, Repository
from pycal_dashboard.templatetags.github import avatar_url

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser

    from pycal_dashboard.github.person_client import PersonClient

    from .project_access import ProjectAccess

LIMIT = 10  # people proposed at most
MIN_SEARCH = 2  # characters typed before GitHub is searched
# what may be searched on GitHub: the characters of GitHub handles
SEARCHABLE = re.compile(r"[A-Za-z0-9-]+")


class HandleCompletion:
    """The people proposed for what a person types into a field of GitHub handles.

    Every field of GitHub handles proposes the same way (``person-complete.js`` and
    ``/complete/people/``): first, in a project, the authors of its pull requests; then the
    people that dashboard.pycal.org knows and the person may see: those who signed in, and
    the authors and reviewers of the repositories of public projects and of the projects of the
    person; then, while fewer than :data:`LIMIT` are found, the accounts of all of GitHub,
    searched with the token of the person. The field of the roles of a project proposes only
    the people who signed in, as only they can get a role (``signed_in``).
    """

    def __init__(
        self,
        user: AbstractBaseUser | AnonymousUser,
        access: ProjectAccess | None = None,
        signed_in: bool = False,
    ):
        """The completion for a person.

        Parameters:
            user: Who types.
            access: The project of the field, with the rights of the person; None for none.
            signed_in: Only the people who signed in, such as for a role.
        """
        self.user = user
        self.access = access
        self.signed_in = signed_in

    @staticmethod
    def clean(text: str) -> str:
        """What was typed, without spaces and a leading ``@``.

        Parameters:
            text: Such as `` @nicco``.

        Returns:
            Such as ``nicco``.

        Examples:
            >>> HandleCompletion.clean(" @nicco ")
            'nicco'
        """
        return text.strip().removeprefix("@")

    @staticmethod
    def person(found: GitHubUser | str, name: str = "") -> dict:
        """A person as the field shows them.

        Parameters:
            found: The account, or a GitHub handle.
            name: The GitHub name for a handle.

        Returns:
            The GitHub handle (``login``), the GitHub name and the address of the avatar.
        """
        if isinstance(found, str):
            return {"login": found, "name": name, "avatar": avatar_url(found, 20)}
        return {"login": found.login, "name": found.name, "avatar": avatar_url(found, 20)}

    def repositories(self) -> Q:
        """The repositories whose people the person may see.

        Returns:
            The repositories of public projects that are not private, and those of the projects
            of the person.
        """
        visible = Q(private=False, projects__public=True)
        if self.user.is_authenticated:
            visible |= Q(projects__members__user=self.user)
        return Q(pk__in=Repository.objects.filter(visible).values("pk"))

    def known(self, text: str) -> list[dict]:
        """The people that the site knows, whose GitHub handle starts or GitHub name has the text.

        Parameters:
            text: What was typed.

        Returns:
            At most :data:`LIMIT` people: the authors of the pull requests of the project first,
            then the others, each by their GitHub handle.
        """
        text = self.clean(text)
        if not text:
            return []
        like = Q(login__istartswith=text) | Q(name__icontains=text)
        groups = []
        if self.access is not None and not self.signed_in:
            shown = self.access.project.repositories.all()
            if not self.access.is_member:  # as the project shows them: not those made private
                shown = shown.filter(private=False)
            groups.append(
                GitHubUser.objects.filter(
                    like, issues__repository__in=shown, issues__pull_request=True
                )
            )
        if self.signed_in:
            groups.append(GitHubUser.objects.filter(like, user__isnull=False))
        else:
            seen = self.repositories()
            groups.append(
                GitHubUser.objects.filter(like).filter(
                    Q(user__isnull=False)
                    | Q(issues__repository__in=Repository.objects.filter(seen))
                    | Q(reviews__issue__repository__in=Repository.objects.filter(seen))
                )
            )
        found: dict[str, dict] = {}
        for group in groups:
            for account in group.distinct().order_by("login")[:LIMIT]:
                found.setdefault(account.login.lower(), self.person(account))
        profiles = Profile.objects.filter(github_name__istartswith=text).exclude(github_name="")
        for profile in profiles.order_by("github_name")[:LIMIT]:
            found.setdefault(profile.github_name.lower(), self.person(profile.github_name))
        return list(found.values())[:LIMIT]

    def searches(self, text: str, found: list[dict]) -> bool:
        """Whether GitHub is searched for more.

        Parameters:
            text: What was typed.
            found: The people found so far.

        Returns:
            True while fewer than :data:`LIMIT` are found, for at least :data:`MIN_SEARCH`
            characters of a GitHub handle; never for the people who signed in only.
        """
        text = self.clean(text)
        return (
            not self.signed_in
            and len(found) < LIMIT
            and len(text) >= MIN_SEARCH
            and SEARCHABLE.fullmatch(text) is not None
        )

    def github(self, text: str, client: PersonClient, found: list[dict]) -> list[dict]:
        """The people found, then accounts of all of GitHub like the text.

        Parameters:
            text: What was typed.
            client: GitHub with the token of the person.
            found: The people found so far.

        Returns:
            At most :data:`LIMIT` people.

        Raises:
            DashboardError: GitHub could not be asked, such as without a token.
        """
        known = {person["login"].lower() for person in found}
        more = [
            self.person(login)
            for login in client.users(self.clean(text))
            if login.lower() not in known
        ]
        return (found + more)[:LIMIT]
