"""Create and change projects: name, description, visibility, repositories and people."""

from django.db import transaction
from django.utils.text import slugify

from pycal_dashboard.errors import (
    LastOwner,
    PersonNotFound,
    PrivateRepositoriesInProject,
    PrivateRepositoryInPublicProject,
    ProjectNameMissing,
    UnknownRole,
)
from pycal_dashboard.models import Profile, Project, ProjectMember, Repository

from .project_access import ProjectAccess

NAME_LENGTH = 100


class ProjectEditor:
    """The changes that a person makes to a project, each checked against their rights."""

    def __init__(self, access: ProjectAccess):
        """An editor of a project.

        Args:
            access: The project with the rights of the person.
        """
        self.access = access
        self.project = access.project

    @staticmethod
    def clean_name(name: str) -> str:
        """The name of a project, checked.

        Args:
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
    def free_slug(name: str) -> str:
        """An address for a new project that no other project has.

        Args:
            name: The name of the project.

        Returns:
            The slug, such as ``icalendar`` or ``icalendar-2``.
        """
        base = slugify(name)[:70] or "project"
        slug, number = base, 1
        while Project.objects.filter(slug=slug).exists():
            number += 1
            slug = f"{base}-{number}"
        return slug

    @classmethod
    @transaction.atomic
    def create(cls, user, name: str, description: str = "", public: bool = True) -> Project:
        """Create a project that the person owns.

        Args:
            user: The person who signed in.
            name: The name.
            description: What the project is about.
            public: Whether everybody sees it.

        Returns:
            The project.

        Raises:
            ProjectNameMissing: The name is empty.
        """
        name = cls.clean_name(name)
        project = Project.objects.create(
            slug=cls.free_slug(name),
            name=name,
            description=description.strip(),
            public=public,
            created_by=user,
        )
        ProjectMember.objects.create(project=project, user=user, role=ProjectMember.OWNER)
        return project

    def change(self, name: str, description: str, public: bool | None = None) -> None:
        """Change the name and the description, and, for owners, whether it is public.

        Args:
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

    def add(self, repository: Repository) -> bool:
        """Add a repository.

        Args:
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

        Args:
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

        Args:
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

        Args:
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

        Args:
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
