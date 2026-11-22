"""The settings of the site that its administrators change on the page Settings."""

from django.core.cache import cache
from django.db import models

CACHE_KEY = "site-settings"


class SiteSettings(models.Model):
    """The settings of the site, one row: what the administrators decide on the page Settings.

    ``image_hosts`` are the hosts whose images texts of Markdown show, such as
    ``insight.pycal.org`` for its badges; images of other sites are not loaded. The privacy
    policy lists them. The pages read the settings from the cache, which a change renews.
    """

    image_hosts = models.JSONField(default=list, blank=True)
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
