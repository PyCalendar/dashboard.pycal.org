"""A person who may read or change a project."""

from django.conf import settings
from django.db import models


class ProjectMember(models.Model):
    """The role of a person in a project, see ``ProjectAccess``.

    Readers see the project, also a private one. Writers also change its name, description and
    repositories and update it. Owners also share it, make it public or private and delete it.
    """

    READ = "read"
    WRITE = "write"
    OWNER = "owner"
    ROLES = [(READ, "read"), (WRITE, "write"), (OWNER, "owner")]
    RANK = {READ: 1, WRITE: 2, OWNER: 3}

    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role = models.CharField(max_length=10, choices=ROLES, default=READ)
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["project", "user__username"]
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="one_role_per_project")
        ]

    def __str__(self) -> str:
        return f"{self.user} {self.role} {self.project}"
