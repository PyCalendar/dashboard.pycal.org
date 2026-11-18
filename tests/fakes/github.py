"""A fake GitHub: the tests never use the network.

The site only talks to GitHub to register its GitHub App (the conversion of the manifest)
and to read the app itself (``GET /app``).
The fake logs every request, so tests can check that the site writes nothing to GitHub.
"""

import re

import httpx


class FakeGitHub:
    """The state of the fake GitHub and the handler of httpx."""

    # what the site may send without changing anything on GitHub
    NOT_WRITING = (r"/app-manifests/[^/]+/conversions",)

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.manifest_codes: dict[str, dict] = {}
        self.fail_with: int | None = None
        self.fail_message = "failure of the fake"
        self.unreachable = False
        # the app as GET /app describes it; the tests change its permissions and events
        from pycal_dashboard.github.permissions import EVENTS, REQUIRED

        self.installations: list[dict] = []  # GET /app/installations
        self.app = {
            "slug": "dashboard-test",
            "owner": {"login": "PyCalendar", "type": "Organization"},
            "permissions": dict(REQUIRED),
            "events": list(EVENTS),
        }

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def writes(self) -> list[httpx.Request]:
        """The requests that would change something on GitHub, such as labels or comments."""
        return [
            r
            for r in self.requests
            if r.method not in ("GET", "HEAD")
            and not any(re.fullmatch(p, r.url.path) for p in self.NOT_WRITING)
        ]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.unreachable:
            raise httpx.ConnectError("no network", request=request)
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"message": self.fail_message})
        if request.method == "GET" and request.url.path == "/app/installations":
            return httpx.Response(200, json=self.installations)
        if request.method == "GET" and request.url.path == "/app":
            if not request.headers.get("Authorization", "").startswith("Bearer ey"):
                return httpx.Response(
                    401, json={"message": "A JSON web token could not be decoded"}
                )
            return httpx.Response(200, json=self.app)
        match = re.fullmatch(r"/app-manifests/(?P<code>[^/]+)/conversions", request.url.path)
        if request.method == "POST" and match and match["code"] in self.manifest_codes:
            return httpx.Response(201, json=self.manifest_codes.pop(match["code"]))
        return httpx.Response(404, json={"message": "Not Found"})
