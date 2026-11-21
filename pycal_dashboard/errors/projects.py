"""Errors of projects: who may do what, the repositories and the collaborators of a project."""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class ProjectError(DashboardError):
    """A project could not be shown or changed.

    Go back to the project, reload it and try again.
    """

    title = _("The project could not be changed")
    guide = "tutorial/projects.html"
    guide_title = _("Projects")


class ProjectNotFound(ProjectError):
    """No project is at this address, or it is private and you are not a collaborator of it.

    Check the address on the page *Projects*. To see a private project, sign in
    with the GitHub account that its owners shared it with.
    """

    title = _("Project not found")
    status = 404


class ProjectReadOnly(ProjectError):
    """You may read this project but not change it.

    Only its writers and owners change a project and update it. Ask an owner of
    the project to give you the role *write*, see :ref:`project-roles`.
    """

    title = _("You may not change this project")
    status = 403


class ProjectOwnersOnly(ProjectError):
    """Only the owners of a project share it, make it public or private and delete it.

    Ask an owner of the project, or ask them for the role *owner*, see
    :ref:`project-roles`.
    """

    title = _("Only the owners may do this")
    status = 403


class ProjectNameMissing(ProjectError):
    """A project needs a name.

    Enter a name of up to 100 characters, such as *icalendar*.
    """

    title = _("The project needs a name")


class RepositoryNameInvalid(ProjectError):
    """The repository is not given as ``owner/name``.

    Enter the account and the name of the repository, such as
    ``collective/icalendar``, or a link to it on GitHub.
    """

    title = _("Not the name of a repository")


class RepositoryNotFound(ProjectError):
    """GitHub knows no repository of this name that you may see.

    Check the name. A private repository can be added only if the GitHub App is
    installed on it and you may read it, see :ref:`private-repositories`.
    """

    title = _("Repository not found")
    status = 404


class PrivateRepositoryInPublicProject(ProjectError):
    """A private repository can only be part of a private project.

    Everybody sees a public project. Make the project private first, then add
    the repository, see :ref:`private-repositories`.
    """

    title = _("A private repository needs a private project")


class PrivateRepositoriesInProject(ProjectError):
    """A project with private repositories cannot be public.

    Remove the private repositories first, or keep the project private, see
    :ref:`private-repositories`.
    """

    title = _("The project has private repositories")


class PersonNotFound(ProjectError):
    """Nobody with this GitHub handle has signed in to the site yet.

    A project is shared with people who have an account on the site. Ask the
    person to sign in with GitHub once, then share the project again.
    """

    title = _("Nobody with this GitHub handle")
    status = 404


class UnknownRole(ProjectError):
    """The form sent a role that the site does not know.

    The roles are *read*, *write* and *owner*. Reload the page and try again.
    """

    title = _("Unknown role")


class LastOwner(ProjectError):
    """A project needs at least one owner.

    Give another person the role *owner* first, then change or remove your own
    role. To end the project, delete it.
    """

    title = _("The project needs an owner")


class GitHubTokenMissing(ProjectError):
    """The site has no token of your GitHub account to list your organizations and repositories.

    Sign out and sign in with GitHub again: GitHub then gives the site a token
    that reads your organizations and public repositories. It never writes.
    """

    title = _("Sign in again to list your repositories")
    status = 401


class GitHubSignInExpired(ProjectError):
    """GitHub no longer accepts the token that the site got when you signed in.

    You revoked the access of the dashboard in your settings on GitHub (*Applications*,
    *Authorized OAuth Apps*), the people who run the site changed or reset its OAuth app, or
    GitHub let the token expire. Sign out and sign in with GitHub again: GitHub then gives the
    site a new token. The GitHub request in the details finds the request at GitHub.
    """

    title = _("Sign in again: GitHub no longer accepts your sign-in")
    status = 401


class BackupInvalid(ProjectError):
    """The file is not a backup of a project that the site can restore.

    A backup is a file of YAML, as *Download the backup* in the settings of a project makes
    it. The details say what is wrong, such as a filter without a name or a step whose filter
    is not in the file. Nothing of the project was changed.
    """

    title = _("The backup cannot be restored")
    status = 400


class BackupVersionUnknown(ProjectError):
    """The backup has a version of its format that this site does not know.

    It was made by a newer version of the site, or it is no backup of the site. Restore it on
    a site of the same version or newer; nothing of the project was changed.
    """

    title = _("The backup has an unknown version")
    status = 400


class ProjectSlugInvalid(ProjectError):
    """The address of a project may only have the letters of a GitHub handle.

    Use a to z, 0 to 9 and single hyphens inside, and at most one ``~`` between
    an account and a repository, such as ``icalendar`` or
    ``collective~icalendar``; up to 80 characters. ``new`` is taken by the site.
    See :ref:`project-address`.
    """

    title = _("Not an address of a project")


class ProjectSlugTaken(ProjectError):
    """Another project has or had this address.

    Addresses are never used twice, so that old links keep leading to their
    project. Choose another one, see :ref:`project-address`.
    """

    title = _("The address is taken")


class FilterNotFound(ProjectError):
    """The project has no saved filter of this number.

    It may have been deleted. Open the tab *Filters* of the project for those it has.
    """

    title = _("Filter not found")
    status = 404


class FilterNameMissing(ProjectError):
    """A filter needs a name.

    Give the filter a name that says what it shows, such as *Ready to merge*.
    """

    title = _("The filter needs a name")
    status = 400


class FilterNameTaken(ProjectError):
    """The project has a filter of this name already.

    The names of the filters of a project are unique: choose another name, or open that filter
    and save it under its name to change it.
    """

    title = _("The project has a filter of this name")
    status = 409


class StepNotFound(ProjectError):
    """The project has no step of this number.

    It may have been removed. Open the tab *Steps* of the project for those it has.
    """

    title = _("Step not found")
    status = 404


class FilterIsAStep(ProjectError):
    """The filter is a step already.

    Each step has its own filter, and a filter is one step at most. Open the tab *Steps* to
    change the step, or save the filter under a new name for another step.
    """

    title = _("The filter is a step already")
    status = 409


class ContributorNotFound(ProjectError):
    """Nobody of this GitHub handle took part in the repositories of the project that you see.

    The page of a person in a project lists the issues and pull requests they opened and the
    reviews they gave in its repositories. Check the handle in the address; the person may
    only have commented, which the page does not count, or worked in a private repository of
    the project that you may not see.
    """

    title = _("Person not found in the project")
    status = 404


class PullRequestNotFound(ProjectError):
    """The project has no pull request of this number that you may see.

    Check the number on the tab *Pull requests* of the project. The repositories of the
    project may not have it, its repository may have been removed from the project, or it is
    private and you are not a collaborator of the project. A new pull request comes with the
    next update of its repository.
    """

    title = _("Pull request not found")
    status = 404


class PullRequestNumberAmbiguous(ProjectError):
    """Several repositories of the project have a pull request of this number.

    Name the repository in the address, such as ``badge.svg?repository=collective/icalendar``.
    The variables ``{pr_badge_url}`` and ``{pr_steps_url}`` of the steps name it when the
    project has several repositories.
    """

    title = _("Which repository?")
    status = 404
