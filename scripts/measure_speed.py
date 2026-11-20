"""Measure the speed of the conditions on a live site, through the JSON of its pages.

Usage: ``make measure-speed``, or with a project and a label::

    uv run python scripts/measure_speed.py --project icalendar --label "needs review"
    uv run python scripts/measure_speed.py --save before.json
    uv run python scripts/measure_speed.py --compare before.json

Each address is read ``--times`` times as a visitor who is not signed in; the table shows the
fastest and the median time and, with ``--compare``, the median of an earlier run and how much
faster it is now. It reads only: the table of the pull requests with every condition as one
column (``col``), the saved filters, the page of a pull request and its badge.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

DEFAULT_URL = "https://dashboard.pycal.org"


class SpeedMeasure:
    """The times of the JSON of the pages of a project, one address after the other."""

    def __init__(self, url: str, project: str, client: httpx.Client | None = None):
        """The project of a site.

        Parameters:
            url: The site, such as ``https://dashboard.pycal.org``.
            project: The slug of a public project, such as ``icalendar``.
            client: The HTTP client; a new one by default.
        """
        self.url = url.rstrip("/")
        self.project = project
        self.client = client or httpx.Client(timeout=120, follow_redirects=True)

    def addresses(self, label: str, number: int | None) -> dict[str, str]:
        """What to measure: a name and its address, each condition as one column.

        Parameters:
            label: A label of the repositories, for the conditions of labels.
            number: A pull request for its page and badge; None to leave them out.

        Returns:
            The addresses by their names.
        """
        table = f"/projects/{self.project}/pull-requests.json?per_page=100"
        columns = {
            "label present": f"labels~applies~present~{label}",
            "label absent": f"labels~applies~absent~{label}",
            "branch up to date": "branch~applies~up_to_date",
            "branch outdated": "branch~applies~outdated",
            "branch conflict": "branch~applies~conflict",
            "ci passing": "ci~applies~passing",
            "ci failing": "ci~applies~failing",
            "ci unknown": "ci~applies~unknown",
            "status open": "status~applies~open",
            "status merged": "status~applies~merged",
            "status auto-merging": "status~applies~auto_merge",
            "reviews at least 1": "reviews~applies~1",
            "author review ratio": "author~applies~review_ratio~1",
            "author reviews given": "author~applies~reviews_given~3",
        }
        found = {"table without columns": table}
        for name, column in columns.items():
            found[name] = f"{table}&col={quote(column, safe='~')}"
        found["all conditions"] = table + "".join(
            f"&col={quote(column, safe='~')}" for column in columns.values()
        )
        found["filters"] = f"/projects/{self.project}/filters.json"
        if number is not None:
            found["pull request"] = f"/projects/{self.project}/pull/{number}.json"
            found["badge"] = f"/projects/{self.project}/pull/{number}/badge.svg"
        return found

    def first_pull_request(self) -> int | None:
        """The number of the newest pull request of the project, for its page and badge."""
        answer = self.client.get(
            f"{self.url}/projects/{self.project}/pull-requests.json?per_page=10"
        )
        pulls = answer.json().get("pull_requests", []) if answer.status_code == 200 else []
        return pulls[0]["number"] if pulls else None

    def time(self, address: str, times: int) -> list[float]:
        """The seconds of each reading of an address.

        Parameters:
            address: The path, such as ``/projects/icalendar/filters.json``.
            times: How many times to read it.

        Returns:
            The seconds; ``inf`` for a reading that failed.
        """
        found = []
        for _ in range(times):
            start = time.perf_counter()
            try:
                answer = self.client.get(self.url + address)
                ok = answer.status_code == 200
            except httpx.HTTPError:
                ok = False
            found.append(time.perf_counter() - start if ok else float("inf"))
        return found

    def run(self, label: str, times: int) -> dict[str, dict]:
        """Measure every address.

        Parameters:
            label: A label of the repositories.
            times: How many times to read each address.

        Returns:
            For each name: its ``address``, the ``fastest`` and the ``median`` seconds.
        """
        results = {}
        for name, address in self.addresses(label, self.first_pull_request()).items():
            seconds = self.time(address, times)
            results[name] = {
                "address": address,
                "fastest": min(seconds),
                "median": statistics.median(seconds),
            }
            print(f"{name:24} {self.cell(results[name]['median'])}", file=sys.stderr)
        return results

    @staticmethod
    def cell(seconds: float) -> str:
        """Seconds as milliseconds for the table, ``failed`` for a failure."""
        return "failed" if seconds == float("inf") else f"{seconds * 1000:8.0f} ms"

    @classmethod
    def table(cls, results: dict[str, dict], before: dict[str, dict] | None = None) -> str:
        """The results as a table of text, compared with an earlier run.

        Parameters:
            results: The results of :meth:`run`.
            before: The results of an earlier run, or None.

        Returns:
            The table.
        """
        head = f"{'what':24} {'fastest':>11} {'median':>11}"
        lines = [head + (f" {'before':>11} {'faster':>7}" if before else "")]
        for name, result in results.items():
            line = f"{name:24} {cls.cell(result['fastest'])} {cls.cell(result['median'])}"
            if before and name in before:
                old = before[name]["median"]
                line += f" {cls.cell(old)}"
                if old not in (0, float("inf")) and result["median"] != float("inf"):
                    line += f" {old / result['median']:6.1f}x"
            lines.append(line)
        return "\n".join(lines)


def main(arguments: list[str] | None = None) -> int:
    """Measure, print the table, save or compare the results.

    Parameters:
        arguments: The arguments of the command line; those of the process by default.

    Returns:
        0, or 1 if an address failed.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--project", default="icalendar")
    parser.add_argument("--label", default="needs review")
    parser.add_argument("--times", type=int, default=3)
    parser.add_argument("--save", type=Path, help="write the results as JSON")
    parser.add_argument("--compare", type=Path, help="the JSON of an earlier run")
    options = parser.parse_args(arguments)
    results = SpeedMeasure(options.url, options.project).run(options.label, options.times)
    before = json.loads(options.compare.read_text()) if options.compare else None
    print(SpeedMeasure.table(results, before))
    if options.save:
        options.save.write_text(json.dumps(results, indent=2))
    return int(any(result["median"] == float("inf") for result in results.values()))


if __name__ == "__main__":
    sys.exit(main())
