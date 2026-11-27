"""An author signs up for the PR message: from the Current Message, through signing in, to Save."""

from playwright.sync_api import expect

from .test_projects import pull_request_project


def test_an_author_signs_up_for_the_pr_message(page, site, github, bob, oauth):
    from pycal_dashboard.models import PullRequestMessage

    project = pull_request_project(github, bob)
    PullRequestMessage.objects.create(project=project, template="Hi {pr_title}", to_authors=True)
    page.goto(f"{site}/projects/icalendar/message/")
    scope = page.locator("[data-signup-link]")
    expect(page.get_by_role("heading", name="Pull Requests with a status message")).to_be_visible()
    scope.get_by_role("link", name="Sign up").click()
    signup = page.locator("[data-message-signup]")
    expect(signup).to_contain_text("Log in to enable the Pull Request Messages")
    expect(signup.locator("[data-signup-repositories] li")).to_have_text(
        ["github.com/collective/icalendar"]
    )
    expect(signup.get_by_role("link")).to_have_count(0)  # nobody gets lost
    signup.get_by_role("button", name="Sign in with GitHub").click()  # carol of the fake GitHub
    expect(signup).to_contain_text("Hello @carol,")
    switch = signup.get_by_role(
        "switch",
        name="Enable Pull Request Messages for all your pull requests on these repositories?",
    )
    expect(switch).not_to_be_checked()  # off by default
    switch.check()
    signup.get_by_role("button", name="Save").click()
    expect(
        page.get_by_text("Your pull requests on these repositories get the PR message.")
    ).to_be_visible()
    expect(switch).to_be_checked()
    assert PullRequestMessage.objects.get().authors == ["carol"]
