"""Create and change projects: name, description, visibility, repositories and people."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from pycal_dashboard import project_slugs
from pycal_dashboard.errors import (
    LastOwner,
    PersonNotFound,
    PrivateRepositoriesInProject,
    PrivateRepositoryInPublicProject,
    ProjectNameMissing,
    ProjectSlugInvalid,
    ProjectSlugTaken,
    UnknownRole,
)
from pycal_dashboard.models import Profile, Project, ProjectMember, ProjectSlug, Repository
from pycal_dashboard.models.project import random_slug

from .project_access import ProjectAccess

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser


NAME_LENGTH = 100


class ProjectEditor:
    """The changes that a person makes to a project, each checked against their rights."""

    def __init__(self, access: ProjectAccess):
        """An editor of a project.

        Parameters:
            access: The project with the rights of the person.
        """
        self.access = access
        self.project = access.project

    @staticmethod
    def clean_name(name: str) -> str:
        """The name of a project, checked.

        Parameters:
            name: What the person entered.

        Returns:
            The name without spaces around it.

        Raises:
            ProjectNameMissing: The name is empty.
        """
        name = " ".join(name.split())[:NAME_LENGTH]
        if not name:
            raise ProjectNameMissing()
        return name

    @staticmethod
    def clean_slug(slug: str, project: Project | None = None) -> str:
        """A slug that a person chose, checked.

        Parameters:
            slug: What the person entered.
            project: The project that gets it, None for a new one.

        Returns:
            The slug in lower case.

        Raises:
            ProjectSlugInvalid: It breaks the rules of slugs.
            ProjectSlugTaken: Another project has or had it.
        """
        slug = slug.strip().lower()
        if not project_slugs.valid(slug):
            raise ProjectSlugInvalid(slug[:100])
        if ProjectSlug.taken(slug, project) or (
            Project.objects.filter(slug=slug).exclude(pk=getattr(project, "pk", None)).exists()
        ):
            raise ProjectSlugTaken(slug)
        return slug

    @classmethod
    @transaction.atomic
    def create(
        cls,
        user: AbstractBaseUser | AnonymousUser,
        name: str,
        description: str = "",
        public: bool = True,
        slug: str = "",
    ) -> Project:
        """Create a project that the person owns.

        Parameters:
            user: The person who signed in.
            name: The name.
            description: What the project is about.
            public: Whether everybody sees it.
            slug: The address that the person chose, "" for a random one.

        Returns:
            The project.

        Raises:
            ProjectNameMissing: The name is empty.
            ProjectSlugInvalid: The slug breaks the rules.
            ProjectSlugTaken: Another project has or had the slug.
        """
        name = cls.clean_name(name)
        project = Project.objects.create(
            slug=cls.clean_slug(slug) if slug.strip() else random_slug(),
            name=name,
            description=description.strip(),
            public=public,
            created_by=user,
        )
        ProjectMember.objects.create(project=project, user=user, role=ProjectMember.OWNER)
        return project

    def change(self, name: str, description: str, public: bool | None = None) -> None:
        """Change the name and the description, and, for owners, whether it is public.

        Parameters:
            name: The new name.
            description: The new description.
            public: Whether everybody sees it; None to keep it.

        Raises:
            ProjectReadOnly: The person may not change the project.
            ProjectOwnersOnly: The person may not make it public or private.
            ProjectNameMissing: The name is empty.
            PrivateRepositoriesInProject: A project with private repositories is made public.
        """
        self.access.require_write()
        self.project.name = self.clean_name(name)
        self.project.description = description.strip()
        if public is not None and public != self.project.public:
            self.access.require_owner()
            if public and self.project.repositories.filter(private=True).exists():
                raise PrivateRepositoriesInProject(self.project.name)
            self.project.public = public
        self.project.save()

    def rename(self, slug: str) -> bool:
        """Give the project another address; the old one keeps leading to it.

        Parameters:
            slug: The new slug.

        Returns:
            False if it is the slug of the project already.

        Raises:
            ProjectOwnersOnly: The person does not own the project.
            ProjectSlugInvalid: The slug breaks the rules.
            ProjectSlugTaken: Another project has or had the slug.
        """
        self.access.require_owner()
        slug = self.clean_slug(slug, self.project)
        if slug == self.project.slug:
            return False
        self.project.slug = slug
        self.project.save()
        return True

    def suggestion(self) -> str | None:
        """A better slug for a project of one repository.

        It is the name of the repository, else account~name, else that with a number.

        Returns:
            The first free slug of ``project_slugs.suggestions``, None for projects of more or
            fewer repositories or that have it already.
        """
        repositories = list(self.project.repositories.all()[:2])
        if len(repositories) != 1:
            return None
        for slug in project_slugs.suggestions(repositories[0].full_name):
            if slug == self.project.slug:
                return None
            if not ProjectSlug.taken(slug, self.project):
                return slug
        return None

    def add(self, repository: Repository) -> bool:
        """Add a repository.

        Parameters:
            repository: The repository, found with ``RepositoryLookup``.

        Returns:
            False if it was in the project already.

        Raises:
            ProjectReadOnly: The person may not change the project.
            PrivateRepositoryInPublicProject: A private repository goes into a public project.
        """
        self.access.require_write()
        if repository.private and self.project.public:
            raise PrivateRepositoryInPublicProject(repository.full_name)
        if self.project.repositories.filter(pk=repository.pk).exists():
            return False
        self.project.repositories.add(repository)
        return True

    def remove(self, repository_id: int) -> Repository | None:
        """Remove a repository; it stays recorded for other projects.

        Parameters:
            repository_id: The id of the repository on the site.

        Returns:
            The repository, None if it was not in the project.

        Raises:
            ProjectReadOnly: The person may not change the project.
        """
        self.access.require_write()
        repository = self.project.repositories.filter(pk=repository_id).first()
        if repository is not None:
            self.project.repositories.remove(repository)
        return repository

    def share(self, github_name: str, role: str) -> ProjectMember:
        """Give a person a role in the project, or change it.

        Parameters:
            github_name: The GitHub name of the person, who signed in before.
            role: ``read``, ``write`` or ``owner``.

        Returns:
            The role of the person.

        Raises:
            ProjectOwnersOnly: The person who shares does not own the project.
            UnknownRole: The role is not one of the site.
            PersonNotFound: Nobody with this GitHub name signed in.
            LastOwner: The last owner would lose the role.
        """
        self.access.require_owner()
        if role not in ProjectMember.RANK:
            raise UnknownRole(role[:50])
        profile = Profile.with_github_name(github_name)
        if profile is None:
            raise PersonNotFound(github_name.strip()[:50])
        member = ProjectMember.objects.filter(project=self.project, user=profile.user).first()
        if member and member.role == ProjectMember.OWNER and role != ProjectMember.OWNER:
            self.keep_an_owner(member)
        member = member or ProjectMember(project=self.project, user=profile.user)
        member.role = role
        member.save()
        return member

    def unshare(self, member_id: int) -> ProjectMember | None:
        """Take the role of a person away.

        Parameters:
            member_id: The id of the role.

        Returns:
            The role taken away, None if there was none.

        Raises:
            ProjectOwnersOnly: The person does not own the project.
            LastOwner: It is the last owner.
        """
        self.access.require_owner()
        member = ProjectMember.objects.filter(project=self.project, pk=member_id).first()
        if member is None:
            return None
        if member.role == ProjectMember.OWNER:
            self.keep_an_owner(member)
        member.delete()
        return member

    def keep_an_owner(self, member: ProjectMember) -> None:
        """Check that another owner stays when a member stops being one.

        Parameters:
            member: The owner who would stop being one.

        Raises:
            LastOwner: No other owner would stay.
        """
        others = self.project.members.filter(role=ProjectMember.OWNER).exclude(pk=member.pk)
        if not others.exists():
            raise LastOwner(self.project.name)

    def delete(self) -> None:
        """Delete the project; its repositories stay recorded for other projects.

        Raises:
            ProjectOwnersOnly: The person does not own the project.
        """
        self.access.require_owner()
        self.project.delete()
