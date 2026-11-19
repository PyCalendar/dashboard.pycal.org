"""A label of a repository on GitHub, as the site read it."""

from django.db import models


class Label(models.Model):
    """A label that a repository has, which issues and pull requests carry (``Issue.labels``).

    The conditions ``label_exists`` and ``label_absent`` check them on a pull request; their
    input is the name of a label of the repository.
    """

    repository = models.ForeignKey("Repository", on_delete=models.CASCADE, related_name="labels")
    github_id = models.BigIntegerField(null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300, blank=True)
    color = models.CharField(max_length=6, blank=True)  # such as d73a4a, without #

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["repository", "name"], name="label_name_unique")
        ]

    def __str__(self) -> str:
        return self.name
