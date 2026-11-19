"""An email of the site, recorded without its addresses: they are private."""

from django.core.mail import send_mail

from .action import Action


class EmailSent(Action):
    """Send an email and record it, without the addresses, in the log."""

    kind = "email"

    def __init__(self, subject: str, body: str, recipients: list[str]):
        """The email.

        Parameters:
            subject: The subject.
            body: The text.
            recipients: The addresses.
        """
        self.subject, self.body, self.recipients = subject, body, recipients

    def perform(self) -> None:
        """Send the email."""
        send_mail(self.subject, self.body, None, self.recipients)

    def text(self) -> str:
        """What was sent, without the addresses.

        Examples:
            >>> EmailSent("New permissions", "", ["a@example.org", "b@example.org"]).text()
            'Email to 2 addresses: New permissions'
        """
        return f"Email to {len(self.recipients)} addresses: {self.subject}"
