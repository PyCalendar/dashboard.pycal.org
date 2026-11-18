"""A label that the GitHub App added to or removed from a pull request."""

from django.db import models


class LabelChange(models.Model):
    """Why a pull request got a label: public for public repositories."""

    repository = models.ForeignKey(
        "Repository", on_delete=models.CASCADE, related_name="label_changes"
    )
    number = models.PositiveIntegerField()
    label = models.CharField(max_length=100)
    added = models.BooleanField()
    rule = models.CharField(max_length=50, blank=True, default="")
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-time", "-pk"]

    def __str__(self) -> str:
        sign = "+" if self.added else "-"
        return f"{self.repository.full_name}#{self.number} {sign}{self.label}"
