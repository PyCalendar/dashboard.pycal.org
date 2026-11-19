"""A fake GitHub: the tests never use the network.

The site registers its GitHub App (the conversion of the manifest), reads the app itself
(``GET /app``) and its installations, and reads repositories: with the token of a person, of an
installation or without one. The fake logs every request, so tests can check that the site
writes nothing to GitHub.
"""

import re

import httpx


class FakeGitHub:
    """The state of the fake GitHub and the handler of httpx."""

    # what the site may send without changing anything on GitHub
    NOT_WRITING = (r"/app-manifests/[^/]+/conversions", r"/app/installations/\d+/access_tokens")
    PERSON_TOKEN = "person-token"  # the token of the OAuth app of the person who signed in

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

        # the repositories: full name -> id, private, description, open_issues_count (issues and
        # pull requests), pulls (open), installation (id or None), collaborators (login: role)
        self.repositories: dict[str, dict] = {}
        self.organizations: list[str] = []  # GET /user/orgs of the person
        self.person_login = "bob"

    def add_repository(
        self,
        full_name: str,
        *,
        private: bool = False,
        issues: int = 0,
        pulls: int = 0,
        installation: int | None = None,
        collaborators: dict | None = None,
        description: str = "",
    ) -> dict:
        """A repository of the fake GitHub.

        Args:
            full_name: owner/name.
            private: Whether it is private.
            issues: Its open issues, without the pull requests.
            pulls: Its open pull requests.
            installation: The id of the installation of the GitHub App on it, None for none.
            collaborators: Who may read it, by login, such as ``{"bob": "write"}``.
            description: Its description.
        """
        repository = {
            "id": 5000 + len(self.repositories),
            "full_name": full_name,
            "name": full_name.split("/")[1],
            "owner": {"login": full_name.split("/")[0]},
            "private": private,
            "description": description,
            "open_issues_count": issues + pulls,
            "pulls": pulls,
            "installation": installation,
            "collaborators": collaborators or {},
        }
        self.repositories[full_name.lower()] = repository
        if installation is not None and not any(
            i["id"] == installation for i in self.installations
        ):
            self.installations.append(
                {
                    "id": installation,
                    "account": {"login": full_name.split("/")[0], "type": "Organization"},
                    "permissions": dict(self.app["permissions"]),
                    "events": list(self.app["events"]),
                }
            )
        return repository

    @staticmethod
    def public(repository: dict) -> dict:
        return {
            k: v
            for k, v in repository.items()
            if k not in ("pulls", "installation", "collaborators")
        }

    def token_of(self, request: httpx.Request) -> str:
        return request.headers.get("Authorization", "").removeprefix("Bearer ").strip()

    def sees(self, request: httpx.Request, repository: dict) -> bool:
        """Whether the token of a request sees a repository: private ones need an installation."""
        if not repository["private"]:
            return True
        return self.token_of(request) == f"installation-{repository['installation']}"

    def repositories_of(self, owner: str) -> list[dict]:
        return [
            self.public(r)
            for r in self.repositories.values()
            if r["owner"]["login"].lower() == owner.lower() and not r["private"]
        ]

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
        answer = self.handle_repositories(request)
        if answer is not None:
            return answer
        match = re.fullmatch(r"/app-manifests/(?P<code>[^/]+)/conversions", request.url.path)
        if request.method == "POST" and match and match["code"] in self.manifest_codes:
            return httpx.Response(201, json=self.manifest_codes.pop(match["code"]))
        return httpx.Response(404, json={"message": "Not Found"})

    def handle_repositories(self, request: httpx.Request) -> httpx.Response | None:
        """The requests about repositories, organizations and installation tokens."""
        path = request.url.path
        token = self.token_of(request)
        match = re.fullmatch(r"/app/installations/(\d+)/access_tokens", path)
        if request.method == "POST" and match:
            if not token.startswith("ey"):
                return httpx.Response(401, json={"message": "A JSON web token is needed"})
            return httpx.Response(201, json={"token": f"installation-{match[1]}"})
        if request.method != "GET":
            return None
        person = token == self.PERSON_TOKEN
        if path == "/user/orgs" and person:
            return httpx.Response(200, json=[{"login": o} for o in self.organizations])
        if path == "/user/repos" and person:
            return httpx.Response(200, json=self.repositories_of(self.person_login))
        match = re.fullmatch(r"/(?:orgs|users)/([^/]+)/repos", path)
        if match:
            if path.startswith("/orgs/") and match[1] not in self.organizations:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(200, json=self.repositories_of(match[1]))
        if path == "/search/repositories":
            words = request.url.params.get("q", "").split()
            text = next((w for w in words if ":" not in w), "").lower()
            user = next((w[5:] for w in words if w.startswith("user:")), "").lower()
            items = [
                self.public(r)
                for r in self.repositories.values()
                if not r["private"]
                and text in r["name"].lower()
                and (not user or r["owner"]["login"].lower() == user)
            ]
            return httpx.Response(200, json={"total_count": len(items), "items": items})
        match = re.fullmatch(r"/repos/([^/]+/[^/]+)(/.*)?", path)
        if not match:
            return None
        repository = self.repositories.get(match[1].lower())
        rest = match[2] or ""
        if repository is None:
            return httpx.Response(404, json={"message": "Not Found"})
        if rest == "/installation":
            if not token.startswith("ey") or repository["installation"] is None:
                return httpx.Response(404, json={"message": "Not Found"})
            installation = next(
                i for i in self.installations if i["id"] == repository["installation"]
            )
            return httpx.Response(200, json=installation)
        if not self.sees(request, repository):
            return httpx.Response(404, json={"message": "Not Found"})
        if rest == "":
            return httpx.Response(200, json=self.public(repository))
        if rest == "/pulls":
            pulls = repository["pulls"]
            page = int(request.url.params.get("page", 1))
            headers = {}
            if pulls > 1 and request.url.params.get("per_page") == "1":
                base = f"https://api.github.com{path}?state=open&per_page=1"
                headers["link"] = (
                    f'<{base}&page={page + 1}>; rel="next", <{base}&page={pulls}>; rel="last"'
                )
            return httpx.Response(
                200, json=[{"number": n} for n in range(min(pulls, 1))], headers=headers
            )
        match = re.fullmatch(r"/collaborators/([^/]+)/permission", rest)
        if match:
            role = repository["collaborators"].get(match[1], "none")
            return httpx.Response(200, json={"permission": role})
        return None
