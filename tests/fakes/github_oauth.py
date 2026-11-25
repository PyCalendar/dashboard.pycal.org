"""The sign in on a fake GitHub: the OAuth app gives a token and tells who signed in.

allauth asks GitHub with ``requests``. The site sends the browser to GitHub to authorize it;
the browser tests send it back to the site instead, as GitHub would after the person agreed
(``authorize``).
"""

import json
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from requests.adapters import BaseAdapter

from tests.fakes.github import FakeGitHub


class FakeOAuth(BaseAdapter):
    """Answers the requests of allauth to GitHub: the token, the person, the addresses."""

    def __init__(self, login: str = "carol", github_id: int = 77):
        super().__init__()
        self.login = login
        self.github_id = github_id
        self.codes: list[str] = []  # the codes that the site exchanged for a token

    def send(self, request, **kwargs):
        url = urlparse(request.url)
        if url.path == "/login/oauth/access_token":
            body = parse_qs(
                request.body if isinstance(request.body, str) else request.body.decode()
            )
            self.codes.append(body.get("code", [""])[0])
            data = {
                "access_token": FakeGitHub.PERSON_TOKEN,
                "token_type": "bearer",
                "scope": "read:org,user:email",
            }
        elif url.path == "/user":
            data = {"id": self.github_id, "login": self.login, "name": "Carol", "avatar_url": ""}
        elif url.path == "/user/emails":
            data = [{"email": f"{self.login}@example.org", "primary": True, "verified": True}]
        else:
            data, status = {"message": "Not Found"}, 404
            return self.answer(request, data, status)
        return self.answer(request, data)

    @staticmethod
    def answer(request, data, status: int = 200) -> requests.Response:
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(data).encode()
        response.headers["Content-Type"] = "application/json"
        response.url = request.url
        response.request = request
        return response

    def close(self):
        pass

    def session(self) -> requests.Session:
        """A session of requests whose requests reach this fake."""
        session = requests.Session()
        session.mount("https://", self)
        return session

    @staticmethod
    def authorize(route) -> None:
        """The site sends the browser to GitHub, where the person agrees: back to the site.

        A form that the site sends on to the sign in, with its method kept (307), such as the
        one that skips a step, is followed first: routes do not see redirects.
        """
        response = route.fetch(max_redirects=0)
        location = response.headers.get("location", "")
        while response.status in (307, 308) and location.startswith("/"):
            # as a browser: the cookies of the redirect, such as a new session, go along
            cookies = dict(
                part.split("=", 1)
                for part in route.request.headers.get("cookie", "").split("; ")
                if "=" in part
            )
            for header in response.headers_array:
                if header["name"].lower() == "set-cookie":
                    name, value = header["value"].split(";", 1)[0].split("=", 1)
                    cookies[name] = value
                    route.request.frame.page.context.add_cookies(
                        [{"name": name, "value": value, "url": route.request.url}]
                    )
            headers = {
                **route.request.headers,
                "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
            }
            response = route.fetch(
                url=urljoin(route.request.url, location), headers=headers, max_redirects=0
            )
            location = response.headers.get("location", "")
        if not location.startswith("https://github.com/login/oauth/authorize"):
            route.fulfill(response=response)
            return
        query = parse_qs(urlparse(location).query)
        code = urlencode({"code": "the-code", "state": query["state"][0]})
        route.fulfill(
            status=302,
            headers={**response.headers, "location": f"{query['redirect_uri'][0]}?{code}"},
        )
