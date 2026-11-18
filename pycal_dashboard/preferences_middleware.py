"""The language that a person chose in the account applies on every device."""

from django.utils import translation

from .models import Preferences


class PreferencesMiddleware:
    """Use the preferences of the person who signed in: the language, and the colors in pages.

    Without a choice in the account, the language of the browser decides, or the choice of the
    language menu in a cookie (``LocaleMiddleware``). The menus save their choice in the account
    of a person who signed in, so the account and the menus agree.
    """

    def __init__(self, get_response):
        """The middleware.

        Args:
            get_response: The next step of Django.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Read the preferences, use their language, then answer.

        Args:
            request: The request.

        Returns:
            The answer.
        """
        request.preferences = Preferences.of(getattr(request, "user", None))
        if request.preferences and request.preferences.language:
            translation.activate(request.preferences.language)
            request.LANGUAGE_CODE = request.preferences.language
        return self.get_response(request)
