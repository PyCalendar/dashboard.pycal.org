"""A fake GitHub: the tests never use the network.

The site registers its GitHub App (the conversion of the manifest), reads the app itself
(``GET /app``) and its installations, and reads repositories: with the token of a person, of an
installation or without one. The fake logs every request, so tests can check that the site
writes nothing to GitHub.
"""

import json
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
        self.fail_html = ""  # with fail_with: a page of HTML instead of JSON, as of a proxy
        self.graphql_max_first = 100  # GitHub gives up (502) on pages of more pull requests
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
        self.issue_requests: list[dict] = []  # the parameters of each GET of the issues
        self.pull_requests_read: list[int] = []  # the numbers of GET /pulls/<number>
        self.graphql_queries: list[dict] = []  # the queries of GraphQL: query and variables
        self.graphql_reviews_queries: list[dict] = []  # those of the reviews of all

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

        Parameters:
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
        repository["issues"] = []  # the issues and pull requests, see add_issue
        repository["labels"] = []  # the labels: id, name, description, color, see add_label
        repository["checks"] = {}  # by commit: (check runs, combined status), see set_checks
        self.repositories[full_name.lower()] = repository
        for _ in range(issues):
            self.add_issue(full_name, "An issue")
        for _ in range(pulls):
            self.add_issue(full_name, "A pull request", pull_request=True)
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

    OCTOCAT = {
        "id": 583231,
        "login": "octocat",
        "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
        "type": "User",
    }

    def add_issue(
        self,
        full_name: str,
        title: str,
        *,
        pull_request: bool = False,
        state: str = "open",
        merged: bool = False,
        user: dict | None = None,
        body: str = "",
        updated: str = "2026-11-01T10:00:00Z",
        labels: tuple[str, ...] = (),
        mergeable_state: str = "clean",
        auto_merge: bool = False,
        closed_by: dict | None = None,
    ) -> dict:
        """An issue or a pull request of a repository of the fake GitHub.

        Parameters:
            full_name: The repository.
            title: Its title.
            pull_request: Whether it is a pull request.
            state: ``open`` or ``closed``.
            merged: Whether the closed pull request was merged.
            user: Who created it, as GitHub describes accounts; octocat by default.
            body: Its description.
            updated: When it changed last, as GitHub writes times.
            labels: The names of its labels, which the repository gets if it lacks them.
            mergeable_state: Of a pull request: clean, dirty, behind, unknown ...
            auto_merge: Whether a pull request has auto-merge enabled.
            closed_by: Who closed it, as GitHub describes accounts; its author by default.

        Returns:
            The issue as GitHub lists it.
        """
        repository = self.repositories[full_name.lower()]
        number = len(repository["issues"]) + 1
        issue = {
            "id": 90000 + 1000 * repository["id"] + number,
            "number": number,
            "title": title,
            "user": dict(user or self.OCTOCAT),
            "body": body or None,
            "state": state,
            "created_at": f"2026-10-{min(number, 28):02d}T09:00:00Z",
            "updated_at": updated,
            "closed_at": "2026-11-01T09:00:00Z" if state == "closed" else None,
            "labels": [self.add_label(full_name, name) for name in labels],
            "reviews": [],  # what GraphQL answers, see add_review()
            "closed_by": dict(closed_by or user or self.OCTOCAT) if state == "closed" else None,
        }
        if pull_request:
            issue["pull_request"] = {
                "url": f"https://api.github.com/repos/{full_name}/pulls/{number}",
                "merged_at": "2026-11-01T09:00:00Z" if merged else None,
            }
            issue["pull"] = {  # what GET /pulls/<number> adds
                "head": {"sha": f"sha{number:037d}", "ref": f"branch-{number}"},
                "base": {"ref": "main"},
                "mergeable": None if mergeable_state == "unknown" else mergeable_state != "dirty",
                "mergeable_state": mergeable_state,
                "auto_merge": {"merge_method": "squash"} if auto_merge else None,
            }
        repository["issues"].append(issue)
        # GitHub counts the open pull requests among the open issues
        repository["open_issues_count"] = sum(i["state"] == "open" for i in repository["issues"])
        repository["pulls"] = sum(
            i["state"] == "open" and "pull_request" in i for i in repository["issues"]
        )
        return issue

    def add_label(self, full_name: str, name: str, description: str = "", color: str = "ededed"):
        """A label of a repository, unless it has one of the name; returns it."""
        labels = self.repositories[full_name.lower()]["labels"]
        for label in labels:
            if label["name"] == name:
                return label
        label = {"id": 7000 + len(labels), "name": name, "description": description, "color": color}
        labels.append(label)
        return label

    def set_checks(self, full_name: str, number: int, rollup: str | None):
        """The state of the checks of the last commit of a pull request, as GraphQL sums them
        up: SUCCESS, FAILURE, ERROR, PENDING, EXPECTED, or None without checks."""
        repository = self.repositories[full_name.lower()]
        sha = repository["issues"][number - 1]["pull"]["head"]["sha"]
        repository["checks"][sha] = rollup

    def add_review(
        self, full_name: str, number: int, user: dict | None = None, state: str = "APPROVED"
    ) -> dict:
        """A review of a pull request, as GraphQL describes it; it changes the pull request.

        Parameters:
            full_name: The repository.
            number: The pull request.
            user: Who gave it, as GitHub describes accounts; octocat by default.
            state: APPROVED, CHANGES_REQUESTED, COMMENTED or DISMISSED.

        Returns:
            The review.
        """
        issue = self.repositories[full_name.lower()]["issues"][number - 1]
        self.review_count = getattr(self, "review_count", 0) + 1
        review = {
            "databaseId": 50000 + self.review_count,
            "state": state,
            "submittedAt": "2026-11-02T09:00:00Z",
            "author": self.actor(user or self.OCTOCAT),
        }
        issue["reviews"].append(review)
        issue["updated_at"] = f"2026-11-02T{min(self.review_count, 59):02d}:00:00Z"
        return review

    @staticmethod
    def actor(user: dict | None) -> dict | None:
        """An account of the REST API as GraphQL describes it."""
        if user is None:
            return None
        return {
            "__typename": user.get("type", "User"),
            "login": user["login"],
            "avatarUrl": user.get("avatar_url", ""),
            "databaseId": user["id"],
        }

    def reviews_page(self, repository: dict, variables: dict) -> httpx.Response:
        """All pull requests, the last changed first, with their reviews and who closed them."""
        pulls = sorted(
            (i for i in repository["issues"] if "pull" in i),
            key=lambda issue: issue["updated_at"],
            reverse=True,
        )
        start = int(variables.get("after") or 0)
        size = variables.get("first", 50)
        nodes = [
            {
                "number": issue["number"],
                "updatedAt": issue["updated_at"],
                "reviews": {"nodes": list(issue["reviews"])},
                "timelineItems": {
                    "nodes": [{"actor": self.actor(issue["closed_by"])}]
                    if issue["state"] == "closed"
                    else []
                },
            }
            for issue in pulls[start : start + size]
        ]
        more = start + size < len(pulls)
        data = {
            "rateLimit": {"cost": 1, "remaining": 4999, "resetAt": "2026-11-19T13:00:00Z"},
            "repository": {
                "pullRequests": {
                    "pageInfo": {
                        "hasNextPage": more,
                        "endCursor": str(start + size) if more else None,
                    },
                    "nodes": nodes,
                }
            },
        }
        return httpx.Response(200, json={"data": data})

    MERGEABLE = {True: "MERGEABLE", False: "CONFLICTING", None: "UNKNOWN"}

    def graphql(self, request: httpx.Request) -> httpx.Response:
        """The query of the open pull requests of a repository, as GitHub answers it.

        The fake does not parse the query: it answers every field the site may ask for.
        """
        if not self.token_of(request):
            return httpx.Response(
                401, json={"message": "This endpoint requires you to be authenticated."}
            )
        body = json.loads(request.content)
        reviews = "orderBy: {field: UPDATED_AT" in body["query"]  # REVIEWS, else the open ones
        (self.graphql_reviews_queries if reviews else self.graphql_queries).append(body)
        variables = body["variables"]
        if variables.get("first", 50) > self.graphql_max_first:
            return httpx.Response(
                502, text="<html><head><title>502 Bad Gateway</title></head></html>"
            )
        repository = self.repositories.get(f"{variables['owner']}/{variables['name']}".lower())
        if repository is None or not self.sees(request, repository):
            error = {"type": "NOT_FOUND", "message": "Could not resolve to a Repository"}
            return httpx.Response(200, json={"data": {"repository": None}, "errors": [error]})
        if reviews:
            return self.reviews_page(repository, variables)
        pulls = [i for i in repository["issues"] if "pull" in i and i["state"] == "open"]
        start = int(variables.get("after") or 0)
        size = variables.get("first", 50)
        page = pulls[start : start + size]
        nodes = []
        for issue in page:
            pull = issue["pull"]
            rollup = repository["checks"].get(pull["head"]["sha"])
            nodes.append(
                {
                    "number": issue["number"],
                    "headRefName": pull["head"]["ref"],
                    "headRefOid": pull["head"]["sha"],
                    "baseRefName": pull["base"]["ref"],
                    "mergeable": self.MERGEABLE[pull["mergeable"]],
                    "mergeStateStatus": pull["mergeable_state"].upper(),
                    "autoMergeRequest": {"enabledAt": "2026-11-01T09:00:00Z"}
                    if pull["auto_merge"]
                    else None,
                    "commits": {
                        "nodes": [
                            {"commit": {"statusCheckRollup": {"state": rollup} if rollup else None}}
                        ]
                    },
                }
            )
        more = start + size < len(pulls)
        data = {
            "rateLimit": {"cost": 1, "remaining": 4999, "resetAt": "2026-11-19T13:00:00Z"},
            "repository": {
                "pullRequests": {
                    "pageInfo": {
                        "hasNextPage": more,
                        "endCursor": str(start + size) if more else None,
                    },
                    "nodes": nodes,
                }
            },
        }
        return httpx.Response(200, json={"data": data})

    @staticmethod
    def public(repository: dict) -> dict:
        return {
            k: v
            for k, v in repository.items()
            if k not in ("pulls", "installation", "collaborators", "issues", "labels", "checks")
        }

    def issues_of(self, request: httpx.Request, repository: dict) -> httpx.Response:
        """A page of the issues and pull requests, as GitHub lists them, with ``since``."""
        params = request.url.params
        items = sorted(repository["issues"], key=lambda i: (i["updated_at"], i["number"]))
        items = [{k: v for k, v in i.items() if k != "pull"} for i in items]
        if params.get("state", "open") != "all":
            items = [i for i in items if i["state"] == params.get("state", "open")]
        if params.get("since"):
            since = params["since"].replace("+00:00", "Z")
            items = [i for i in items if i["updated_at"] >= since]
        per_page, page = int(params.get("per_page", 30)), int(params.get("page", 1))
        self.issue_requests.append(dict(params))
        return httpx.Response(200, json=items[(page - 1) * per_page : page * per_page])

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
            and not (r.url.path == "/graphql" and b"mutation" not in r.content)  # a query reads
        ]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.unreachable:
            raise httpx.ConnectError("no network", request=request)
        if self.fail_with and self.fail_html:
            return httpx.Response(
                self.fail_with,
                text=self.fail_html,
                headers={"content-type": "text/html", "x-github-request-id": "C0DE:1234:5678"},
            )
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
        if request.method == "POST" and request.url.path == "/graphql":
            return self.graphql(request)
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
        match = re.fullmatch(r"/repos/([^/]+/[^/]+)/issues/(\d+)/labels", path)
        if request.method == "POST" and match and token.startswith("installation-"):
            repository = self.repositories[match[1].lower()]
            issue = repository["issues"][int(match[2]) - 1]
            for name in json.loads(request.content)["labels"]:  # a new one is created
                label = self.add_label(match[1], name)
                if label not in issue["labels"]:
                    issue["labels"].append(label)
            return httpx.Response(200, json=issue["labels"])
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
        if rest == "/issues":
            return self.issues_of(request, repository)
        if rest == "/labels":
            page = int(request.url.params.get("page", 1))
            per_page = int(request.url.params.get("per_page", 30))
            labels = repository["labels"][(page - 1) * per_page : page * per_page]
            return httpx.Response(200, json=labels)
        match = re.fullmatch(r"/pulls/(\d+)", rest)
        if match:
            issue = next((i for i in repository["issues"] if i["number"] == int(match[1])), None)
            if issue is None or "pull" not in issue:
                return httpx.Response(404, json={"message": "Not Found"})
            self.pull_requests_read.append(int(match[1]))
            data = {k: v for k, v in issue.items() if k not in ("pull", "pull_request")}
            return httpx.Response(200, json={**data, **issue["pull"]})
        match = re.fullmatch(r"/commits/([0-9a-z]+)/(check-runs|status)", rest)
        if match:
            runs, status = repository["checks"].get(
                match[1], ([], {"state": "pending", "total_count": 0})
            )
            if match[2] == "check-runs":
                return httpx.Response(200, json={"total_count": len(runs), "check_runs": runs})
            return httpx.Response(200, json=status)
        match = re.fullmatch(r"/collaborators/([^/]+)/permission", rest)
        if match:
            role = repository["collaborators"].get(match[1], "none")
            return httpx.Response(200, json={"permission": role})
        return None
