"""Skipping quality checks: in the dialog of a writer, and with the link of the author."""

import re

from playwright.sync_api import expect

from tests.fakes.github import FakeGitHub

from .test_projects import pull_request_project

REVIEW = "labels~applies~present~needs review"


def review_steps(project):
    """A step Review with the label as its quality check, and a step Open after it."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    steps = []
    for position, (name, column) in enumerate(
        (("Review", REVIEW), ("Open", "status~applies~open"))
    ):
        saved = PullRequestFilter.objects.create(project=project, name=name, columns=[column])
        steps.append(
            PullRequestStep.objects.create(
                project=project,
                filter=saved,
                name=name,
                position=position,
                conditions={column: {"summary": f"Pass {name.lower()}"}},
            )
        )
    return steps


def test_a_writer_skips_a_quality_check(signed_in, site, github, bob):
    """Skip in the quality check, the reason in Markdown, ✕ closes the dialog; then the next step."""
    review, _open = review_steps(pull_request_project(github, bob))
    page = signed_in
    page.goto(f"{site}/projects/icalendar/pull/1/?step={review.pk}")
    task = page.locator("[data-tasks] [data-task]")
    expect(task).to_have_attribute("data-task", "todo")
    task.locator("[data-skip-check]").click()  # the dialog pops out
    dialog = page.locator("[data-skip-dialog]:popover-open")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name="Close").click()  # ✕
    expect(dialog).to_have_count(0)
    task.locator("[data-skip-check]").click()
    dialog.get_by_label("Why can the quality check Pass review be skipped?").fill(
        "Reviewed at **the meeting** for {pr_title}"
    )
    dialog.get_by_role("button", name="Skip the quality check Pass review").click()
    expect(page.get_by_text("A quality check of the step Review is skipped.")).to_be_visible()
    first = page.locator("[data-progress] [data-step]").nth(0)
    expect(first).to_have_attribute("data-stage", "past")  # complete: the next step
    expect(page.locator("[data-progress] [data-step]").nth(1)).to_have_attribute("data-current", "")
    task = page.locator("[data-tasks] [data-task]")
    expect(task).to_have_attribute("data-task", "skipped")
    task.locator("summary").click()
    expect(task.locator("[data-skip-reason] strong")).to_have_text("the meeting")
    expect(task.locator("[data-skip-reason]")).to_contain_text("for {pr_title}")
    task.get_by_role("button", name="Don't skip").click()
    expect(page.locator("[data-tasks] [data-task]")).to_have_attribute("data-task", "todo")


def test_the_author_skips_with_their_link_after_signing_in(page, site, github, bob, oauth):
    """The link opens the dialog; the visitor signs in from it, and the skip is made."""
    from pycal_dashboard.models import CheckSkip, Issue
    from pycal_dashboard.services.skip_link import SkipLink

    project = pull_request_project(github, bob)
    review, _open = review_steps(project)
    oauth.login, oauth.github_id = "octocat", FakeGitHub.OCTOCAT["id"]  # the author signs in
    link = SkipLink(project, Issue.objects.get(title="Ready"), review).url(REVIEW, author=True)
    address = link.replace("https://dashboard.example.org", site)
    page.goto(address)
    dialog = page.locator("dialog[open][data-skip-dialog]")
    expect(dialog).to_be_visible()
    dialog.get_by_role("link", name="Close").click()  # ✕: the step without the dialog
    expect(page.locator("dialog[open]")).to_have_count(0)
    expect(page).to_have_url(re.compile(rf"\?repository=collective%2Ficalendar&step={review.pk}$"))
    page.goto(address)
    dialog.get_by_label("Why can the quality check Pass review be skipped?").fill("A typo")
    dialog.get_by_role("button", name="Sign in with GitHub").click()
    expect(page.get_by_text("A quality check of the step Review is skipped.")).to_be_visible()
    expect(page.locator(".account-menu summary")).to_contain_text("octocat")
    skip = CheckSkip.objects.get()
    assert (skip.user.username, skip.reason, skip.condition) == ("octocat", "A typo", REVIEW)
    expect(page.locator("[data-tasks] [data-task]")).to_have_attribute("data-task", "skipped")


def test_who_may_not_skip_sees_the_error_and_the_reason(page, site, github, bob, oauth):
    """carol signs in from the link of the author, but is not the author."""
    from pycal_dashboard.models import CheckSkip, Issue
    from pycal_dashboard.services.skip_link import SkipLink

    project = pull_request_project(github, bob)
    review, _open = review_steps(project)
    link = SkipLink(project, Issue.objects.get(title="Ready"), review).url(REVIEW, author=True)
    page.goto(link.replace("https://dashboard.example.org", site))
    dialog = page.locator("dialog[open][data-skip-dialog]")
    dialog.get_by_label("Why can the quality check Pass review be skipped?").fill("Mine")
    dialog.get_by_role("button", name="Sign in with GitHub").click()
    expect(dialog.locator("[data-skip-error]")).to_contain_text("You may not skip this")
    expect(dialog.locator("[data-skip-error]")).to_contain_text("You signed in as @carol.")
    expect(dialog.get_by_label("Why can the quality check Pass review be skipped?")).to_have_value(
        "Mine"
    )
    assert not CheckSkip.objects.exists()
