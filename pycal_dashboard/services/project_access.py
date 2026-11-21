"""Who may do what with a project: read, write, own; the site administrators may do all."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet

from pycal_dashboard.errors import ProjectNotFound, ProjectOwnersOnly, ProjectReadOnly
from pycal_dashboard.models import Project, ProjectMember, ProjectSlug

from .identity import GitHubIdentity

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser


class ProjectAccess:
    """The rights of a person in a project.

    ========================================  =======  ======  =====  =====
    Action                                    Visitor  Read    Write  Owner
    ========================================  =======  ======  =====  =====
    See a public project                      yes      yes     yes    yes
    See a private project                     no       yes     yes    yes
    See the private repositories of it        no       yes     yes    yes
    Change name, description, repositories    no       no      yes    yes
    Update it from GitHub                     no       no      yes    yes
    Add collaborators, change their roles     no       no      no     yes
    Share it, make it public, delete it       no       no      no     yes
    ========================================  =======  ======  =====  =====

    Everybody who signed in creates projects and owns them. The administrators of the site
    (``SITE_ADMINS``) have the rights of an owner in every project.
    """

    def __init__(self, project: Project, user: AbstractBaseUser | AnonymousUser):
        """The rights of a person.

        Parameters:
            project: The project.
            user: The person, maybe a visitor who did not sign in.
        """
        self.project = project
        self.user = user
        self.admin = GitHubIdentity.is_site_admin(user)
        member = None
        if getattr(user, "is_authenticated", False):
            member = ProjectMember.objects.filter(project=project, user=user).first()
        self.role = ProjectMember.OWNER if self.admin else (member.role if member else "")

    def rank(self) -> int:
        """The role as a number: 0 for none, then read, write, owner."""
        return ProjectMember.RANK.get(self.role, 0)

    @property
    def can_read(self) -> bool:
        """Whether the person sees the project and its private repositories."""
        return self.project.public or self.rank() >= 1

    @property
    def is_member(self) -> bool:
        """Whether the person has a role, and so sees the private repositories."""
        return self.rank() >= 1

    @property
    def can_write(self) -> bool:
        """Whether the person changes the project and updates it."""
        return self.rank() >= ProjectMember.RANK[ProjectMember.WRITE]

    @property
    def is_owner(self) -> bool:
        """Whether the person shares the project, makes it public or private and deletes it."""
        return self.rank() >= ProjectMember.RANK[ProjectMember.OWNER]

    def require_read(self) -> ProjectAccess:
        """Check that the person sees the project.

        Returns:
            These rights.

        Raises:
            ProjectNotFound: The project is private and the person has no role in it.
        """
        if not self.can_read:
            raise ProjectNotFound(self.project.slug)
        return self

    def require_write(self) -> ProjectAccess:
        """Check that the person changes the project.

        Returns:
            These rights.

        Raises:
            ProjectNotFound: The person does not see the project.
            ProjectReadOnly: The person only reads it.
        """
        if not self.require_read().can_write:
            raise ProjectReadOnly(self.project.name)
        return self

    def require_owner(self) -> ProjectAccess:
        """Check that the person owns the project.

        Returns:
            These rights.

        Raises:
            ProjectNotFound: The person does not see the project.
            ProjectOwnersOnly: The person does not own it.
        """
        if not self.require_read().is_owner:
            raise ProjectOwnersOnly(self.project.name)
        return self

    @classmethod
    def of(cls, slug: str, user: AbstractBaseUser | AnonymousUser) -> ProjectAccess:
        """The project of an address with the rights of a person, if they see it.

        An old slug of a project, or one in other case, finds it too: the pages then lead to its
        address (``project.slug``).

        Parameters:
            slug: The project in the address.
            user: The person.

        Returns:
            The rights, with the project.

        Raises:
            ProjectNotFound: There is no such project that the person sees.
        """
        slug = slug.lower()
        project = Project.objects.filter(slug=slug).first()
        if project is None:
            old = ProjectSlug.objects.filter(slug=slug).select_related("project").first()
            project = old.project if old else None
        if project is None:
            raise ProjectNotFound(slug)
        return cls(project, user).require_read()

    @staticmethod
    def visible(user: AbstractBaseUser | AnonymousUser) -> QuerySet:
        """The projects that a person sees: the public ones and those they have a role in.

        Parameters:
            user: The person, maybe a visitor.

        Returns:
            The projects.
        """
        if GitHubIdentity.is_site_admin(user):
            return Project.objects.all()
        allowed = Q(public=True)
        if getattr(user, "is_authenticated", False):
            allowed |= Q(members__user=user)
        return Project.objects.filter(allowed).distinct()
