"""Errors of projects: who may do what, the repositories and the collaborators of a project."""

from django.utils.translation import gettext_lazy as _

from .base import DashboardError


class ProjectError(DashboardError):
    """A project could not be shown or changed.

    Resolve:
        Go back to the project, reload it and try again.
    """

    title = _("The project could not be changed")
    guide = "tutorial/projects.html"
    guide_title = _("Projects")


class ProjectNotFound(ProjectError):
    """No project that you may see is at this address.

    This happens when:

    - the address is wrong, or it leads to a page of a project that does not exist, or
    - the project is private and you are not a collaborator of it, or you did not sign in with
      the GitHub account that its owners shared it with.

    Resolve:
        - When the address may be wrong, check it on the page *Projects*.
        - When the project is private, sign in with the GitHub account that its owners shared it
          with, see :ref:`project-roles`.
    """

    title = _("Project not found")
    status = 404


class ProjectReadOnly(ProjectError):
    """Your role in the project does not allow you to change it or to update it.

    This happens when:

    - you have the role *read* and tried to change the project, or
    - you have no role in the project and tried to change it or to update it from GitHub.

    Resolve:
        - To change the project, ask an owner of the project to give you the role *write*, see
          :ref:`project-roles`.
        - To update it from GitHub, ask an owner of the project for the role *read* at least.

    Context:
        Readers update a project from GitHub but change nothing; its writers and owners change
        it and update it.
    """

    title = _("You may not change this project")
    status = 403


class ProjectOwnersOnly(ProjectError):
    """Only the owners of a project may do what you tried.

    Resolve:
        Ask an owner of the project to do it, or to give you the role *owner*, see
        :ref:`project-roles`.

    Context:
        Only the owners share a project and change the roles in it, make it public or private,
        change its address, restore a backup, delete its snapshots, switch its step labels off
        and delete it.
    """

    title = _("Only the owners may do this")
    status = 403


class ProjectNameMissing(ProjectError):
    """The name of the project is empty, but a project needs a name.

    Resolve:
        Enter a name of up to 100 characters, such as *icalendar*.
    """

    title = _("The project needs a name")


class RepositoryNameInvalid(ProjectError):
    """The repository is not given as ``owner/name``.

    Resolve:
        Enter the account and the name of the repository, such as ``collective/icalendar``, or a
        link to it on GitHub.
    """

    title = _("Not the name of a repository")


class RepositoryNotFound(ProjectError):
    """GitHub knows no repository of this name that you may see.

    This happens when:

    - the name is wrong,
    - the repository is private and the GitHub App is not installed on it, or
    - the repository is private and you may not read it on GitHub.

    Resolve:
        - Check the name.
        - When the repository is private, make sure that the GitHub App is installed on it and
          that you may read it, see :ref:`private-repositories`.

    Context:
        A private repository can be added only if the GitHub App is installed on it and you may
        read it.
    """

    title = _("Repository not found")
    status = 404


class PrivateRepositoryInPublicProject(ProjectError):
    """A private repository can only be part of a private project, not of this public one.

    Resolve:
        Make the project private first, then add the repository, see
        :ref:`private-repositories`.

    Context:
        Everybody sees a public project.
    """

    title = _("A private repository needs a private project")


class PrivateRepositoriesInProject(ProjectError):
    """You made a project with private repositories public, but such a project cannot be public.

    Resolve:
        - To make the project public, remove its private repositories first, see
          :ref:`private-repositories`.
        - Else keep the project private.
    """

    title = _("The project has private repositories")


class PersonNotFound(ProjectError):
    """Nobody with this GitHub handle has signed in to the dashboard yet.

    Resolve:
        - Check the GitHub handle, such as *niccokunzmann*.
        - When it is right, ask the person to sign in with GitHub once, then share the project
          again.

    Context:
        A project is shared with people who have an account on the dashboard.
    """

    title = _("Nobody with this GitHub handle")
    status = 404


class UnknownRole(ProjectError):
    """The form sent a role that the dashboard does not know.

    Resolve:
        Reload the page and try again.

    Context:
        The roles are *read*, *write* and *owner*.
    """

    title = _("Unknown role")


class LastOwner(ProjectError):
    """A project needs at least one owner, and this change would leave it without one.

    Resolve:
        - To change or remove the role, give another person the role *owner* first.
        - To end the project, delete it.
    """

    title = _("The project needs an owner")


class GitHubTokenMissing(ProjectError):
    """The dashboard has no GitHub token of yours to list your organizations and repositories.

    Resolve:
        Sign out and sign in with GitHub again.

    Context:
        When you sign in, GitHub gives the dashboard a token that reads your organizations and
        public repositories. It never writes.
    """

    title = _("Sign in again to list your repositories")
    status = 401


class GitHubSignInExpired(ProjectError):
    """GitHub no longer accepts the token that the dashboard got when you signed in.

    This happens when:

    - you revoked the access of the dashboard in your settings on GitHub (*Applications*,
      *Authorized OAuth Apps*),
    - the people who run the dashboard changed or reset its OAuth app, or
    - the token expired.

    Resolve:
        Sign out and sign in with GitHub again.

    Context:
        The dashboard reads GitHub with the token that GitHub gives it when you sign in. Signing
        in again gives it a new token.

    Note:
        The GitHub request in the details identifies the request at GitHub, such as for its
        support.
    """

    title = _("Sign in again: GitHub no longer accepts your sign-in")
    status = 401


class BackupInvalid(ProjectError):
    """The file is not a backup of a project that the dashboard can restore.

    This happens when:

    - no file was chosen,
    - the file is larger than 1,000,000 bytes, or not a text in UTF-8,
    - it is not YAML, or YAML but no backup of a project (``dashboard_backup`` is missing), or
    - a part of it is missing or wrong, such as a filter without a name or a step whose filter
      is not in the file.

    Resolve:
        - When no file was chosen, choose the file of the backup.
        - When the file was changed by hand, correct the part that the details name.
        - Else restore a file that *Download the backup* in the settings of a project made.

    Context:
        A backup is a file of YAML, as *Download the backup* in the settings of a project makes
        it. Nothing of the project was changed.

    Note:
        The details say what is wrong.
    """

    title = _("The backup cannot be restored")
    status = 400


class BackupVersionUnknown(ProjectError):
    """The backup has a version of its format that this dashboard does not know.

    This happens when:

    - the backup was made by a newer version of the dashboard, or
    - it is no backup of the dashboard.

    Resolve:
        Restore it on a dashboard of the same version or newer.

    Context:
        Nothing of the project was changed.

    Note:
        The details name the version in the file.
    """

    title = _("The backup has an unknown version")
    status = 400


class ProjectSlugInvalid(ProjectError):
    """The address that you chose for the project breaks the rules of the addresses of projects.

    Resolve:
        Use a to z, 0 to 9 and single hyphens inside, and at most one ``~`` between an account
        and a repository, such as ``icalendar`` or ``collective~icalendar``; up to 80
        characters. Do not use ``new``, which is taken by the dashboard. See
        :ref:`project-address`.

    Context:
        The address of a project may only have the letters of a GitHub handle.
    """

    title = _("Not an address of a project")


class ProjectSlugTaken(ProjectError):
    """Another project has or had this address.

    Resolve:
        Choose another address, see :ref:`project-address`.

    Context:
        Addresses are never used twice, so that old links keep leading to their project.
    """

    title = _("The address is taken")


class FilterNotFound(ProjectError):
    """The project has no saved filter of this number.

    This happens when the filter was deleted, or when the address has a wrong number.

    Resolve:
        Open the tab *Filters* of the project for those it has.
    """

    title = _("Filter not found")
    status = 404


class FilterNameMissing(ProjectError):
    """The name of the filter is empty, but a filter needs a name.

    Resolve:
        Give the filter a name that says what it shows, such as *Ready to merge*.
    """

    title = _("The filter needs a name")
    status = 400


class FilterNameTaken(ProjectError):
    """The project has a filter of this name already.

    Resolve:
        - Choose another name.
        - To change that filter, open it and save it under its name.

    Context:
        The names of the filters of a project are unique. Usually the page asks whether to
        replace the other filter; this error appears when another filter got the name while you
        saved.
    """

    title = _("The project has a filter of this name")
    status = 409


class StepNotFound(ProjectError):
    """The project has no step of this number.

    This happens when the step was removed, or when the address or the form has a wrong number.

    Resolve:
        Open the tab *Steps* of the project for those it has.
    """

    title = _("Step not found")
    status = 404


class SnapshotNotFound(ProjectError):
    """The project has no snapshot of this id.

    This happens when:

    - the snapshot was deleted, or
    - the project kept only its newest snapshots.

    Resolve:
        Open the tab *Snapshots* of the settings of the project for those it has.
    """

    title = _("Snapshot not found")
    status = 404


class SkipReasonMissing(ProjectError):
    """You skipped a step for a pull request without a reason, but a step is skipped only with one.

    Resolve:
        Write why the pull request skips the step, such as *The maintainers reviewed it at the
        meeting*.

    Context:
        Only the writers and owners of the project see the reason.
    """

    title = _("The reason to skip the step is missing")
    status = 400


class FilterIsAStep(ProjectError):
    """The filter that you chose for a new step is a step already, or you chose no filter.

    Resolve:
        - To change the step of the filter, open the tab *Steps*.
        - For another step, save the filter under a new name and choose that one.
        - When you chose no filter, choose one.

    Context:
        Each step has its own filter, and a filter is one step at most.
    """

    title = _("The filter is a step already")
    status = 409


class PullRequestNotFound(ProjectError):
    """The project has no pull request of this number that you may see.

    This happens when:

    - the repositories of the project do not have it, or the address names another
      repository,
    - its repository was removed from the project,
    - the pull request is new and the dashboard has not read it yet, or
    - it is private and you are not a collaborator of the project.

    Resolve:
        - Check the number on the tab *Pull requests* of the project.
        - When the pull request is new, wait for the next update of its repository.
        - When it is private, sign in with the GitHub account that the owners of the project
          shared it with, see :ref:`project-roles`.
    """

    title = _("Pull request not found")
    status = 404


class PullRequestNumberAmbiguous(ProjectError):
    """Several repositories of the project have a pull request of this number.

    This happens when the address of the badge or of the PR message names none of them.

    Resolve:
        Name the repository in the address, such as
        ``badge.svg?repository=collective/icalendar``.

    Context:
        The variables ``{pr_badge_url}`` and ``{pr_steps_url}`` of the steps name it when the
        project has several repositories.
    """

    title = _("Which repository?")
    status = 404
