"""The script that measures the speed of the conditions on a live site, without the network."""

import json

import httpx

from scripts.measure_speed import SpeedMeasure, main


def site(failing: frozenset[str] = frozenset()) -> httpx.Client:
    """A site that answers every page; addresses with a part of *failing* answer 500."""
    asked = []

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append(str(request.url))
        if any(part in str(request.url) for part in failing):
            return httpx.Response(500)
        if request.url.path.endswith("pull-requests.json"):
            return httpx.Response(200, json={"pull_requests": [{"number": 42}]})
        return httpx.Response(200, json={})

    client = httpx.Client(transport=httpx.MockTransport(answer))
    client.asked = asked
    return client


def test_every_condition_is_measured():
    client = site()
    results = SpeedMeasure("https://dashboard.example.org/", "icalendar", client).run("bug", 2)
    assert {"label present", "reviews at least 1", "author review ratio", "filters"} <= set(results)
    assert results["badge"]["address"] == "/projects/icalendar/pull/42/badge.svg"
    assert "col=labels~applies~present~bug" in results["label present"]["address"]
    assert results["all conditions"]["address"].count("&col=") == 14
    assert all(r["fastest"] <= r["median"] < 1 for r in results.values())
    assert all(url.startswith("https://dashboard.example.org/") for url in client.asked)


def test_a_failure_is_shown_and_compared():
    client = site(failing=frozenset({"filters.json"}))
    results = SpeedMeasure("https://x.example", "p", client).run("b", 1)
    assert results["filters"]["median"] == float("inf")
    before = {"filters": {"median": 2.0}, "table without columns": {"median": 1.0}}
    lines = SpeedMeasure.table(results, before).split("\n")
    assert "before" in lines[0] and "faster" in lines[0]
    assert "failed" in next(line for line in lines if line.startswith("filters"))


def test_the_command_saves_and_compares(tmp_path, monkeypatch, capsys):
    client = site()  # before httpx.Client is replaced
    monkeypatch.setattr("scripts.measure_speed.httpx.Client", lambda **kwargs: client)
    saved = tmp_path / "before.json"
    assert main(["--url", "https://x.example", "--times", "1", "--save", str(saved)]) == 0
    assert "filters" in json.loads(saved.read_text())
    assert main(["--url", "https://x.example", "--times", "1", "--compare", str(saved)]) == 0
    assert "faster" in capsys.readouterr().out
