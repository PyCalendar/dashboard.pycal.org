"""A fake GitHub: the tests never use the network.

It knows installations, repositories, issues and pull requests, and answers the requests
that the site sends with httpx. It has no route that writes: the site only reads.
"""

import re
from urllib.parse import parse_qs

import httpx

NOW = "2026-11-18T09:30:00Z"


class FakeGitHub:
    """The state of the fake GitHub and the handler of httpx."""

    def __init__(self):
        self.installations: dict[int, dict] = {}
        self.installation_repositories: dict[int, list[str]] = {}
        self.repositories: dict[str, dict] = {}
        self.items: dict[str, list[dict]] = {}  # issues and pull requests by repository
        self.requests: list[httpx.Request] = []
        self.manifest_codes: dict[str, dict] = {}
        self.fail_with: int | None = None
        self.fail_message = "failure of the fake"
        self.unreachable = False

    # --- setting up the state -------------------------------------------------

    def repository(self, full_name: str, private: bool = False, **extra) -> dict:
        if full_name not in self.repositories:
            owner, name = full_name.split("/")
            self.repositories[full_name] = {
                "id": 1000 + len(self.repositories),
                "full_name": full_name,
                "name": name,
                "owner": {"login": owner, "type": "Organization"},
                "private": private,
                "archived": False,
                "fork": False,
                "description": f"The repository {name}",
                "html_url": f"https://github.com/{full_name}",
                "default_branch": "main",
                "language": "Python",
                "topics": [],
                "stargazers_count": 5,
                "forks_count": 2,
                "pushed_at": NOW,
                **extra,
            }
            self.items.setdefault(full_name, [])
        return self.repositories[full_name]

    def install(
        self, installation_id: int, account: str, repositories: list[str], permissions=None
    ):
        from pycal_dashboard.github.permissions import REQUIRED

        self.installations[installation_id] = {
            "id": installation_id,
            "account": {"login": account, "type": "Organization"},
            "permissions": dict(REQUIRED) if permissions is None else permissions,
            "suspended_at": None,
        }
        self.installation_repositories[installation_id] = list(repositories)
        for name in repositories:
            self.repository(name)
        return self.installations[installation_id]

    def issue(self, full_name: str, number: int, author: str = "alice", **extra) -> dict:
        data = {
            "number": number,
            "title": f"Issue {number}",
            "state": "open",
            "user": {"login": author, "type": "User"},
            "author_association": "CONTRIBUTOR",
            "labels": [],
            "comments": 0,
            "html_url": f"https://github.com/{full_name}/issues/{number}",
            "created_at": NOW,
            "updated_at": NOW,
            "closed_at": None,
            **extra,
        }
        data["labels"] = [{"name": n} if isinstance(n, str) else n for n in data["labels"]]
        self.items[full_name].append(data)
        return data

    def pull(
        self, full_name: str, number: int, author: str = "alice", additions=5, deletions=2, **extra
    ) -> dict:
        defaults = {
            "title": f"Pull request {number}",
            "html_url": f"https://github.com/{full_name}/pull/{number}",
            "pull_request": {"merged_at": None},
            "draft": False,
            "requested_reviewers": [],
            "head": {"sha": f"sha{number}"},
        }
        data = self.issue(full_name, number, author, **{**defaults, **extra})
        data["additions"], data["deletions"] = additions, deletions
        return data

    def find(self, full_name: str, number: int) -> dict | None:
        return next((i for i in self.items.get(full_name, []) if i["number"] == number), None)

    # what the site may send without changing anything on GitHub
    NOT_WRITING = (r"/app-manifests/[^/]+/conversions", r"/app/installations/\d+/access_tokens")

    def writes(self) -> list[httpx.Request]:
        """The requests that would change something on GitHub, such as labels or comments."""
        return [
            r
            for r in self.requests
            if r.method not in ("GET", "HEAD")
            and not any(re.fullmatch(p, r.url.path) for p in self.NOT_WRITING)
        ]

    # --- answering -------------------------------------------------------------

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    ROUTES = [
        ("POST", r"/app-manifests/(?P<code>[^/]+)/conversions", "manifest_conversion"),
        ("GET", r"/app/installations", "list_installations"),
        ("GET", r"/app/installations/(?P<id>\d+)", "get_installation"),
        ("POST", r"/app/installations/(?P<id>\d+)/access_tokens", "access_token"),
        ("GET", r"/installation/repositories", "installation_repositories_list"),
        ("GET", r"/repos/(?P<repo>[^/]+/[^/]+)/issues", "list_issues"),
        ("GET", r"/repos/(?P<repo>[^/]+/[^/]+)/pulls", "list_pulls"),
        ("GET", r"/repos/(?P<repo>[^/]+/[^/]+)/pulls/(?P<n>\d+)", "get_pull"),
    ]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.unreachable:
            raise httpx.ConnectError("no network", request=request)
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"message": self.fail_message})
        for method, pattern, name in self.ROUTES:
            match = re.fullmatch(pattern, request.url.path)
            if method == request.method and match:
                return getattr(self, name)(request, **match.groupdict())
        return self.not_found()

    @staticmethod
    def not_found() -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    @staticmethod
    def page(request: httpx.Request, items: list) -> list:
        query = parse_qs(request.url.query.decode())
        per_page = int(query.get("per_page", ["30"])[0])
        number = int(query.get("page", ["1"])[0])
        return items[(number - 1) * per_page : number * per_page]

    def manifest_conversion(self, request, code):
        if code not in self.manifest_codes:
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(201, json=self.manifest_codes.pop(code))

    def list_installations(self, request):
        return httpx.Response(200, json=self.page(request, list(self.installations.values())))

    def get_installation(self, request, id):
        if int(id) not in self.installations:
            return self.not_found()
        return httpx.Response(200, json=self.installations[int(id)])

    def access_token(self, request, id):
        if int(id) not in self.installations:
            return self.not_found()
        return httpx.Response(
            201, json={"token": f"installation-{id}", "expires_at": "2099-01-01T00:00:00Z"}
        )

    def installation_repositories_list(self, request):
        token = request.headers["Authorization"].split("-")[-1]
        names = self.installation_repositories[int(token)]
        repos = [self.repositories[name] for name in names]
        return httpx.Response(
            200, json={"total_count": len(repos), "repositories": self.page(request, repos)}
        )

    def list_issues(self, request, repo):
        items = [
            {
                k: v
                for k, v in i.items()
                if k not in ("additions", "deletions", "requested_reviewers", "head")
            }
            for i in self.items.get(repo, [])
        ]
        return httpx.Response(200, json=self.page(request, items))

    def list_pulls(self, request, repo):
        state = parse_qs(request.url.query.decode()).get("state", ["open"])[0]
        pulls = [
            {k: v for k, v in i.items() if k not in ("additions", "deletions", "pull_request")}
            for i in self.items.get(repo, [])
            if "pull_request" in i and (state == "all" or i["state"] == state)
        ]
        return httpx.Response(200, json=self.page(request, pulls))

    def get_pull(self, request, repo, n):
        found = self.find(repo, int(n))
        if not found or "pull_request" not in found:
            return self.not_found()
        return httpx.Response(200, json={k: v for k, v in found.items() if k != "pull_request"})
