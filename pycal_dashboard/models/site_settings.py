"""The settings of the site that its administrators change on the page Settings."""

from django.core.cache import cache
from django.db import models

CACHE_KEY = "site-settings"
# the hosts whose images load before the administrators change them: the badges of shields.io,
# the images that people put on GitHub, and the sites of pycal.org, such as insight.pycal.org
DEFAULT_IMAGE_HOSTS = ("*.shields.io", "github.com", "*.pycal.org")


def default_image_hosts() -> list[str]:
    """The hosts whose images load by default, :data:`DEFAULT_IMAGE_HOSTS`.

    Returns:
        A new list of them.
    """
    return list(DEFAULT_IMAGE_HOSTS)


class SiteSettings(models.Model):
    """The settings of the site, one row: what the administrators decide on the page Settings.

    ``image_hosts`` are the hosts whose images texts of Markdown show, such as
    ``insight.pycal.org`` for its badges, or ``*.pycal.org`` for all hosts below pycal.org;
    images of other sites are not loaded. They are :data:`DEFAULT_IMAGE_HOSTS` until the
    administrators save others. The privacy policy lists them. The pages read the settings from
    the cache, which a change renews.
    """

    image_hosts = models.JSONField(default=default_image_hosts, blank=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "site settings"

    def __str__(self) -> str:
        return "site settings"

    def save(self, *args: object, **kwargs: object) -> None:
        """Keep the one row, and renew the cache.

        Parameters:
            *args: Those of Django.
            **kwargs: Those of Django.
        """
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)

    @classmethod
    def current(cls) -> "SiteSettings":
        """The settings, from the cache; the defaults before anybody saved them.

        Returns:
            The settings.
        """
        found = cache.get(CACHE_KEY)
        if found is None:
            found = cls.objects.filter(pk=1).first() or cls(pk=1)
            cache.set(CACHE_KEY, found, 300)
        return found
