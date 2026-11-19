"""The trigger of a webhook: what GitHub told the site, in words for people."""

from pycal_dashboard.models import LogTrigger


class WebhookTrigger:
    """Scope and describe the trigger of a webhook once it was handled."""

    @classmethod
    def complete(cls, trigger: LogTrigger, event: str, payload: dict, done: str) -> None:
        """Set the repository, the person and the summary of the trigger of a webhook.

        Parameters:
            trigger: The trigger.
            event: ``X-GitHub-Event``, such as ``pull_request``.
            payload: The webhook.
            done: What the site did, from the handler, or the code of an error.
        """
        repository = payload.get("repository") or {}
        trigger.repository = str(repository.get("full_name") or "")[:200]
        sender = payload.get("sender") or {}
        trigger.actor_login = str(sender.get("login") or "")[:100]
        trigger.summary = f"{cls.describe(event, payload)}: {done}"[:300]
        trigger.save()

    @staticmethod
    def describe(event: str, payload: dict) -> str:
        """A webhook in words.

        Parameters:
            event: ``X-GitHub-Event``.
            payload: The webhook.

        Returns:
            Such as ``Pull request #3 opened: Fix``.

        Examples:
            >>> WebhookTrigger.describe("pull_request", {"action": "opened",
            ...     "pull_request": {"number": 3, "title": "Fix"}})
            'Pull request #3 opened: Fix'
            >>> WebhookTrigger.describe("ping", {})
            'Ping of GitHub'
            >>> WebhookTrigger.describe("installation", {"action": "created",
            ...     "installation": {"account": {"login": "PyCalendar"}}})
            'GitHub App installation created by PyCalendar'
        """
        action = str(payload.get("action", ""))
        if event == "pull_request":
            pull = payload.get("pull_request") or {}
            return f"Pull request #{pull.get('number')} {action}: {pull.get('title', '')}"
        if event in ("issues", "issue_comment"):
            issue = payload.get("issue") or {}
            what = "Comment of issue" if event == "issue_comment" else "Issue"
            return f"{what} #{issue.get('number')} {action}"
        if event == "pull_request_review":
            pull = payload.get("pull_request") or {}
            return f"Review of pull request #{pull.get('number')} {action}"
        if event == "repository":
            return f"Repository {action}"
        if event == "ping":
            return "Ping of GitHub"
        if event in ("installation", "installation_repositories"):
            account = ((payload.get("installation") or {}).get("account") or {}).get("login")
            return f"GitHub App {event.replace('_', ' ')} {action} by {account}"
        return f"Webhook {event} {action}".strip()
