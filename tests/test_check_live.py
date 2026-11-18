"""make check-live: the walk through a live site, here against the site of the tests."""

import httpx
import pytest

from scripts.check_live import LiveCheck

pytestmark = pytest.mark.django_db


def django_transport(client):
    """Answer the requests of the check with the Django test client."""

    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        if request.method == "POST":
            answer = client.generic(
                "POST",
                path,
                request.content,
                content_type="application/json",
                HTTP_X_GITHUB_EVENT=request.headers.get("x-github-event", ""),
            )
        else:
            answer = client.get(path)
        headers = {key: value for key, value in answer.items()}
        body = b"".join(answer.streaming_content) if answer.streaming else answer.content
        return httpx.Response(answer.status_code, headers=headers, content=body)

    return httpx.MockTransport(handle)


def check(client) -> LiveCheck:
    transport = httpx.Client(transport=django_transport(client), base_url="http://testserver")
    return LiveCheck("http://testserver", client=transport, wait=0)


def test_the_site_of_the_tests_passes(client, capsys, settings):
    settings.FAVICON = ""
    live = check(client)
    assert live.run() == 0, live.failures
    for page in ("/", "/about/", "/licenses/", "/health/", "/accounts/login/"):
        assert live.checked.get(page) == 200, page
    for json in ("/index.json", "/about.json", "/licenses.json"):
        assert live.checked.get(json) == 200, json
    assert live.checked.get("/licenses/AGPL-3.0-or-later/") == 200
    assert "0 failures" in capsys.readouterr().out


def test_an_error_page_with_500_fails_the_check(db, monkeypatch):
    from pycal_dashboard import build_info

    def broken(source_url):
        raise RuntimeError("broken")

    monkeypatch.setattr(build_info, "get", broken)  # the start and About pages fail
    from django.test import Client

    live = check(Client(raise_request_exception=False))
    assert live.run() == 1


def test_a_public_page_that_asks_to_sign_in_fails():
    def handle(request):
        return httpx.Response(302, headers={"location": "/accounts/login/?next=/about/"})

    live = LiveCheck("http://site", client=httpx.Client(transport=httpx.MockTransport(handle)))
    live.check_page("/about/")
    assert "public, but asks to sign in" in live.failures[0]


def test_a_redirect_away_from_the_site_fails():
    def handle(request):
        return httpx.Response(302, headers={"location": "https://elsewhere.example/"})

    live = LiveCheck("http://site", client=httpx.Client(transport=httpx.MockTransport(handle)))
    live.check_page("/about/")
    assert "leaves to https://elsewhere.example/" in live.failures[0]
    live.check_page("/favicon.ico")  # the icon may be elsewhere
    assert len(live.failures) == 1


def test_it_waits_while_the_site_starts(monkeypatch):
    answers = iter([502, 503, 200])
    transport = httpx.MockTransport(lambda request: httpx.Response(next(answers)))
    live = LiveCheck("http://site", client=httpx.Client(transport=transport), wait=60)
    monkeypatch.setattr("scripts.check_live.time.sleep", lambda seconds: None)
    assert live.wait_until_up()


def test_it_gives_up_after_the_time(monkeypatch):
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    live = LiveCheck("http://site", client=httpx.Client(transport=transport), wait=0)
    assert not live.wait_until_up()
    assert "did not start" in live.failures[0]


def test_a_500_instead_of_a_404_fails():
    transport = httpx.MockTransport(lambda request: httpx.Response(500, text="Server Error"))
    live = LiveCheck("http://site", client=httpx.Client(transport=transport))
    live.expect("/missing/", (404,))
    assert live.failures and "expected 404" in live.failures[0]


def test_a_404_without_the_page_of_the_site_fails():
    transport = httpx.MockTransport(lambda request: httpx.Response(404, text="Not Found"))
    live = LiveCheck("http://site", client=httpx.Client(transport=transport))
    live.expect("/missing/", (404,))
    assert "error page of the site" in live.failures[0]


def test_the_sign_in_page_does_not_nest_its_address(client):
    page = client.get("/accounts/login/?next=/about/").content.decode()
    assert "next=/accounts/login/" not in page and "next=%2Faccounts" not in page


@pytest.mark.parametrize(
    ("answer", "problem"),
    [
        (httpx.Response(404, json={}), "expected 200"),
        (httpx.Response(200, text="<html>"), "not JSON"),
        (httpx.Response(200, json={}), "other sites may not read it"),
        (
            httpx.Response(
                200,
                content=b"{",
                headers={"content-type": "application/json", "access-control-allow-origin": "*"},
            ),
            "invalid JSON",
        ),
    ],
)
def test_the_json_of_a_page_must_be_readable(answer, problem):
    live = LiveCheck(
        "http://site", client=httpx.Client(transport=httpx.MockTransport(lambda r: answer))
    )
    live.check_json("/about/")
    assert problem in live.failures[0] and "/about.json" in live.failures[0]


def test_a_timeout_is_tried_again(monkeypatch):
    answers = iter([httpx.ReadTimeout("slow"), httpx.Response(200, text="<html>")])

    def handle(request):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr("scripts.check_live.time.sleep", lambda seconds: None)
    live = LiveCheck("http://site", client=httpx.Client(transport=httpx.MockTransport(handle)))
    assert live.get("/licenses/").status_code == 200


def test_no_answer_is_a_failure_not_a_crash(monkeypatch):
    def handle(request):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr("scripts.check_live.time.sleep", lambda seconds: None)
    live = LiveCheck("http://site", client=httpx.Client(transport=httpx.MockTransport(handle)))
    live.check_page("/licenses/")
    assert "599" in live.failures[0] and "/licenses/" in live.failures[0]
