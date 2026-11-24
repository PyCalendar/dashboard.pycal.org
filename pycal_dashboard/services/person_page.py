"""The page of a person of GitHub on dashboard.pycal.org: the projects they took part in."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.db.models import F, Q

from pycal_dashboard.errors import GitHubHandleInvalid
from pycal_dashboard.models import GitHubUser, Issue, Review

from .project_access import ProjectAccess

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser

# the GitHub handles in the addresses: the characters of GitHub, as long as GitHub allows
LOGIN = re.compile(r"[A-Za-z0-9-]{1,39}")


class PersonPage:
    """A person of GitHub, as a visitor may see them on dashboard.pycal.org.

    Every GitHub handle has its page, also of people that dashboard.pycal.org does not know: it
    lists the projects that the visitor sees in which the person opened issues or pull
    requests, reviewed pull requests of others, or skipped a step. Their GitHub name shows only
    when they took part in one of them, so that the page tells nothing of private repositories.
    """

    def __init__(self, login: str, user: AbstractBaseUser | AnonymousUser):
        """The page of a GitHub handle for a visitor.

        Parameters:
            login: The GitHub handle, in any case.
            user: Who looks at the page.

        Raises:
            GitHubHandleInvalid: The text cannot be a GitHub handle.
        """
        if LOGIN.fullmatch(login) is None:
            raise GitHubHandleInvalid(login)
        self.login = login
        self.user = user

    def projects(self) -> list[dict]:
        """The projects that the visitor sees and the person took part in, by their name.

        Returns:
            For each project: ``project``, and the numbers of ``pull_requests``, ``issues`` and
            ``reviews`` (not those on their own pull requests, as by default in a project) in
            the repositories of the project that the visitor sees.
        """
        issues = Issue.objects.filter(author__login__iexact=self.login)
        reviews = Review.objects.filter(author__login__iexact=self.login).exclude(
            author=F("issue__author")
        )
        touched = Q(repositories__in=issues.values("repository")) | Q(
            repositories__in=reviews.values("issue__repository")
        )
        skipped = Q(steps__skips__user__github_user__login__iexact=self.login)
        found = []
        visible = ProjectAccess.visible(self.user).filter(touched | skipped).distinct()
        for project in visible.order_by("name"):
            access = ProjectAccess(project, self.user)
            repositories = project.repositories.all()
            if not access.is_member:  # as the project shows them: not those made private
                repositories = repositories.filter(private=False)
            mine = issues.filter(repository__in=repositories)
            counts = {
                "pull_requests": mine.filter(pull_request=True).count(),
                "issues": mine.filter(pull_request=False).count(),
                "reviews": reviews.filter(issue__repository__in=repositories).count(),
            }
            if (
                any(counts.values())
                or project.steps.filter(skips__user__github_user__login__iexact=self.login).exists()
            ):
                found.append({"project": project, **counts})
        return found

    def person(self, taken_part: bool) -> GitHubUser:
        """The account of GitHub to show.

        Parameters:
            taken_part: Whether the person took part in a project that the visitor sees.

        Returns:
            The account that dashboard.pycal.org knows when the person took part, else one with
            the GitHub handle alone (not saved).
        """
        if taken_part:
            known = GitHubUser.objects.filter(login__iexact=self.login).order_by("pk").first()
            if known is not None:
                return known
        return GitHubUser(login=self.login)
