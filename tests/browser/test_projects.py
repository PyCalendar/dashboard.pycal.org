"""The flows of people in the browser: sign in with GitHub, create a project, share it."""

import re

from playwright.sync_api import expect

from pycal_dashboard.models import Profile, Project


def test_sign_in_with_github(page, site, oauth):
    """From the start page through GitHub, which the fake authorizes, back to the site."""
    page.goto(f"{site}/projects/")
    page.get_by_role("link", name="Sign in with GitHub").click()
    expect(page.get_by_role("heading", name="Sign in with GitHub")).to_be_visible()
    page.get_by_role("button", name="Sign in with GitHub").click()
    expect(page).to_have_url(f"{site}/projects/")
    expect(page.locator(".account-menu summary")).to_contain_text("carol")
    assert oauth.codes == ["the-code"]
    profile = Profile.objects.get(github_name="carol")
    assert profile.github_id == "77"
    assert profile.user.socialaccount_set.get().socialtoken_set.exists()  # lists the repositories
    page.goto(f"{site}/account/")
    expect(page.get_by_role("heading", name="Account · @carol")).to_be_visible()


def test_create_a_project(signed_in, site, github, update_worker):
    """Create a project, add repositories in two ways, see the app step, see them read."""
    page = signed_in
    github.organizations = ["PyCalendar"]
    github.add_repository("collective/icalendar", issues=3, pulls=2, installation=11)
    github.add_repository("PyCalendar/plann", issues=1)
    page.goto(f"{site}/")
    page.get_by_role("link", name="Projects").first.click()
    page.get_by_role("link", name="+ Create a project").click()
    page.get_by_label("Name").fill("iCalendar")
    page.get_by_label("Description").fill("The calendars of Python")
    page.get_by_role("button", name="Create the project").click()
    expect(
        page.get_by_text("The project iCalendar is created. Add its repositories.")
    ).to_be_visible()

    # by name, with the proposals of the field
    field = page.get_by_label("Repository", exact=True)
    expect(field).to_have_attribute("data-complete-connected", "")
    field.fill("ical")
    expect(
        page.locator("#repository-choices option[value='collective/icalendar']")
    ).to_be_attached()
    field.fill("collective/icalendar")
    page.locator("[data-add-by-name]").get_by_role("button", name="Add").click()
    expect(page.get_by_text("collective/icalendar is added.")).to_be_visible()
    expect(
        page.locator("[data-repository='collective/icalendar'] [data-app-installed]")
    ).to_be_visible()

    # from an organization
    page.get_by_label("Organization or account").select_option("PyCalendar")
    page.get_by_role("button", name="Show repositories").click()
    page.get_by_label("plann").check()
    page.locator("[data-owner-repositories]").get_by_role(
        "button", name="Add the chosen repositories"
    ).click()
    expect(page.get_by_text("PyCalendar/plann is added.")).to_be_visible()

    # the next step: the app on the repositories without it
    install = page.locator("[data-install-step]")
    expect(install).to_contain_text("1 repository has no GitHub App yet.")
    expect(
        install.get_by_role("link", name="Install the GitHub App", exact=True)
    ).to_have_attribute("href", "https://github.com/apps/dashboard-test/installations/new")
    expect(
        install.get_by_role("link", name="The permissions it asks for and why")
    ).to_have_attribute("href", "https://docs.example.org/reference/permissions.html")

    # the overview: the added repositories are read in the background at once
    page.get_by_role("link", name="Go to the overview").click()
    expect(page.locator("[data-status='never']")).to_have_count(0)
    expect(page.locator("[data-status='current']")).to_contain_text("Up to date", timeout=15000)
    page.get_by_role("button", name="Update").click()  # and again, when asked
    expect(page.locator("[data-status='current']")).to_contain_text("Up to date", timeout=15000)
    expect(page.locator("[data-open-issues] strong")).to_have_text("4")
    expect(page.locator("[data-open-pull-requests] strong")).to_have_text("2")
    expect(page.locator("[data-last-updated]")).not_to_contain_text("never")
    expect(page.locator("[data-repository='collective/icalendar']")).to_contain_text("3")
    assert Project.objects.get().updated is not None

    # the pull requests of all its repositories, from the tile with their number
    page.locator("[data-open-pull-requests] a").click()
    expect(page).to_have_url(re.compile(r"/projects/[0-9a-f]{6}/pull-requests/$"))
    expect(page.get_by_role("link", name="Pull requests")).to_have_attribute("aria-current", "page")
    expect(page.locator("[data-pull-request]")).to_have_count(2)
    expect(page.locator("[data-pull-request] [data-github-user='octocat']").first).to_be_visible()
    # the columns: hidden by CSS, the choice kept by the browser
    table = page.locator("[data-pull-requests]")
    expect(table.locator("[data-columns-shown]")).to_have_text("Title, Step, Number, Creator")
    expect(table.locator("td.col-title").first).to_be_visible()
    expect(table.locator("td.col-status").first).to_be_hidden()
    expect(table.locator("td.col-link").first).to_be_hidden()  # the title and number link
    row = table.locator("tr[data-status='open']").first
    expect(row).to_have_css("border-left-color", "rgb(29, 107, 51)")  # open: green
    table.get_by_text("Display:").click()
    table.get_by_label("Title").uncheck()
    table.get_by_label("Number", exact=True).uncheck()
    expect(table.locator("td.col-title").first).to_be_hidden()
    expect(table.locator("td.col-link").first).to_be_visible()  # now the icon links
    expect(table.locator("[data-columns-shown]")).to_have_text("Step, Creator")
    table.get_by_label("Status").check()
    expect(row).to_have_css("border-left-style", "none")
    page.reload()
    expect(page.locator("td.col-title").first).to_be_hidden()
    expect(page.locator("td.col-status").first).to_be_visible()
    page.get_by_label("Per page").select_option("10")
    expect(page).to_have_url(re.compile(r"per_page=10"))
    assert github.writes() == []


def test_share_a_project(signed_in, site, alice):
    """The owner gives another person a role by their GitHub handle, which the field proposes."""
    page = signed_in
    page.goto(f"{site}/projects/new/")
    page.get_by_label("Name").fill("Shared")
    expect(page.get_by_label("Public")).to_be_checked()  # the default
    page.get_by_label("Private").check()
    page.get_by_role("button", name="Create the project").click()
    page.get_by_role("link", name="Collaborators").click()
    expect(page.get_by_label("GitHub handle")).to_have_attribute("data-complete-connected", "")
    page.get_by_label("GitHub handle").press_sequentially("ali")
    proposal = page.get_by_role("option", name="@alice")
    expect(proposal.locator("img.avatar")).to_have_count(1)
    proposal.click()
    expect(page.get_by_label("GitHub handle")).to_have_value("alice")
    page.locator("[data-share]").get_by_label("Role", exact=True).select_option("write")
    page.get_by_role("button", name="Share").click()
    expect(page.get_by_text("@alice may change the project.")).to_be_visible()
    expect(page.locator("[data-member='alice']")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/projects/[0-9a-f]{6}/collaborators/$"))


def test_give_a_project_a_short_address(signed_in, site, github):
    """A project of one repository takes the suggested address; the old one still leads to it."""
    page = signed_in
    github.add_repository("collective/icalendar")
    page.goto(f"{site}/projects/new/")
    page.get_by_label("Name").fill("iCalendar")
    page.get_by_role("button", name="Create the project").click()
    expect(page).to_have_url(re.compile(r"/projects/[0-9a-f]{6}/repositories/$"))
    old = page.url
    page.get_by_label("Repository", exact=True).fill("collective/icalendar")
    page.locator("[data-add-by-name]").get_by_role("button", name="Add").click()
    suggestion = page.locator("[data-suggestion]")
    expect(suggestion).to_contain_text("icalendar")
    suggestion.get_by_role("button", name="Use it").click()
    expect(page).to_have_url(f"{site}/projects/icalendar/repositories/")
    expect(
        page.get_by_text("The address of the project is /projects/icalendar/ now")
    ).to_be_visible()
    page.goto(old)
    expect(page).to_have_url(f"{site}/projects/icalendar/repositories/")

    page.get_by_role("link", name="Settings").click()
    page.locator("[data-rename]").get_by_label("Address").fill("pycal~ical")
    page.get_by_role("button", name="Change the address").click()
    expect(page).to_have_url(f"{site}/projects/pycal~ical/settings/")
    expect(page.locator("[data-old-slugs]")).to_contain_text("icalendar")


def test_describe_a_project_in_markdown(signed_in, site):
    """The bar above the description formats it; the preview shows it as the page will."""
    page = signed_in
    page.goto(f"{site}/projects/new/")
    page.get_by_label("Name").fill("iCalendar")
    field = page.locator("[data-markdown-field]")
    expect(field).to_have_attribute("data-markdown-connected", "")
    description = page.get_by_label("Description", exact=True)
    description.fill("calendars")
    description.select_text()
    field.get_by_role("button", name="Bold").click()
    expect(description).to_have_value("**calendars**")
    field.get_by_role("button", name="Preview").click()
    expect(field.locator("[data-markdown-shown] strong")).to_have_text("calendars")
    expect(description).to_be_hidden()
    field.get_by_role("button", name="Write").click()
    expect(description).to_be_visible()
    page.get_by_role("button", name="Create the project").click()
    page.get_by_role("link", name="Overview", exact=True).click()
    expect(page.locator("[data-description] strong")).to_have_text("calendars")


def test_click_away_the_notice_of_failed_updates(page, site, github, bob):
    """The notice of failed updates hides when clicked away, also after a reload."""
    from pycal_dashboard.models import Repository
    from pycal_dashboard.services.project_editor import ProjectEditor
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    github.add_repository("collective/icalendar", installation=11)
    repository = Repository.objects.create(full_name="collective/icalendar")
    project = ProjectEditor.create(bob, "iCalendar")
    project.repositories.add(repository)
    github.fail_with = 502
    github.fail_html = "<html><head><title>502 Bad Gateway</title></head></html>"
    RepositoryUpdate(repository).run()
    page.goto(f"{site}{project.path()}")
    notice = page.locator("[data-update-errors]")
    expect(notice).to_contain_text("1 repository could not be updated")
    notice.get_by_text("Details to copy").click()
    expect(notice.locator("textarea")).to_contain_text("GitHubUnavailable")
    notice.get_by_role("button", name="Hide this notice").click()
    expect(notice).to_be_hidden()
    page.reload()
    expect(page.locator("[data-update-errors]")).to_be_hidden()


def pull_request_project(github, bob):
    """A project with pull requests of all kinds, read from the fake GitHub."""
    from pycal_dashboard.models import Repository
    from pycal_dashboard.services.project_editor import ProjectEditor
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    github.add_repository("collective/icalendar", installation=11)
    github.add_label("collective/icalendar", "needs review", "", "fbca04")
    github.add_issue("collective/icalendar", "Ready", pull_request=True, labels=("needs review",))
    github.add_issue("collective/icalendar", "Conflict", pull_request=True, mergeable_state="dirty")
    github.add_issue("collective/icalendar", "Behind", pull_request=True, mergeable_state="behind")
    repository = Repository.objects.create(full_name="collective/icalendar")
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    RepositoryUpdate(repository).run()
    return project


def test_columns_of_conditions(page, site, github, bob):
    """Add a column with +, filter by it, change it with its gear, add another, drag it."""
    pull_request_project(github, bob)
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    expect(menu.get_by_label("Name of the label")).to_be_visible()  # Label comes first
    page.locator("[data-add-condition]").get_by_role("button", name="Close").click()  # the cross
    expect(menu).to_be_hidden()
    page.get_by_label("Add a condition").click()
    page.keyboard.press("Escape")  # so does Escape
    expect(menu).to_be_hidden()
    page.get_by_label("Add a condition").click()
    menu.get_by_label("Condition").select_option("branch")
    expect(menu.get_by_label("Name of the label")).to_be_hidden()
    menu.get_by_text("outdated", exact=True).click()
    menu.get_by_text("conflict", exact=True).click()
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=branch~all~outdated~conflict"))
    expect(page.locator("[data-pull-request]")).to_have_count(3)
    expect(page.locator(".result-no")).to_have_count(1)
    expect(page.locator(".result-no")).to_have_attribute("aria-label", "does not apply")
    # the toggles: without the crosses, then without the check marks: the crosses come back
    page.get_by_role("button", name="Show those it does not apply to").click()
    expect(page.locator("[data-pull-request]")).to_have_count(2)
    page.get_by_role("button", name="Show those it applies to").click()
    expect(page.locator("[data-pull-request]")).to_have_count(1)
    expect(page.get_by_role("button", name="Show those it does not apply to")).to_have_attribute(
        "aria-pressed", "true"
    )
    page.get_by_role("button", name="Show those it applies to").click()  # both again
    expect(page.locator("[data-pull-request]")).to_have_count(3)
    # its gear: other states
    page.get_by_label("Change the column").click()
    gear = page.locator("[data-condition-column='0'] [data-condition-form]")
    gear.get_by_text("outdated", exact=True).click()
    gear.get_by_role("button", name="Change the column").click()
    expect(page).to_have_url(re.compile(r"col=branch~all~conflict&"))
    # a second column: a label, chosen from those of the repositories
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    menu.get_by_role("button", name="Add the column").click()  # the browser asks for a label
    expect(page).not_to_have_url(re.compile(r"col=labels"))
    menu.get_by_label("Name of the label").fill("needs review")
    menu.get_by_role("button", name="Add the column").click()
    expect(page.locator(".label-chip").first).to_have_text("needs review")
    heads = page.locator("th.col-condition")
    expect(heads.nth(1).locator(".label-chip")).to_have_text("needs review")
    heads.nth(1).drag_to(heads.nth(0))
    expect(page).to_have_url(re.compile(r"col=labels~[^&]+&col=branch"))


def test_the_table_in_german_on_a_phone(page, site, github, bob):
    """German takes much space: the page, its table and its menus fit a phone."""
    pull_request_project(github, bob)
    page.set_viewport_size({"width": 360, "height": 740})
    page.goto(f"{site}/language/")  # the language of the menu: German
    page.context.add_cookies([{"name": "django_language", "value": "de", "url": site}])
    columns = "col=branch~all~up_to_date~outdated~conflict&col=status~all~open~auto_merge"
    page.goto(f"{site}/projects/icalendar/pull-requests/?{columns}")
    expect(page.get_by_role("heading", name="3 Pull Requests")).to_be_visible()
    expect(page.locator("[data-per-page-submit]")).to_be_hidden()  # the menu changes at once
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    page.get_by_text("Anzeigen:").click()
    for column in ("Status", "Organisation", "Repository", "Erstellt"):
        page.locator("[data-columns]").get_by_label(column, exact=True).check()
    assert page.evaluate("document.documentElement.scrollWidth") <= 360  # the table scrolls
    # the script writes the times in the language of the page, as the server translated it
    expect(page.locator("td.col-created time").first).to_contain_text("am ")
    expect(page.locator("td.col-created time").first).not_to_contain_text("on ")
    page.get_by_label("Eine Bedingung hinzufügen").click()
    panel = page.locator("[data-add-condition] .menu-panel")
    expect(panel).to_be_visible()
    box = panel.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 360
    assert page.evaluate("document.documentElement.scrollWidth") <= 360


def test_the_bar_at_the_top_is_one_row_on_a_phone(page, site, signed_in):
    """The projects, the account, the language and the colors side by side, also on a phone."""
    page.set_viewport_size({"width": 360, "height": 740})
    page.goto(f"{site}/projects/")
    tops = [
        round(page.locator(selector).first.bounding_box()["y"])
        for selector in (
            ".nav nav a[href='/projects/']",
            ".account-menu summary",
            ".theme-menu summary",
        )
    ]
    assert max(tops) - min(tops) < 20, tops


def test_save_a_filter_and_open_it_again(signed_in, site, github, bob):
    """Save the columns as a filter, with the suggested opposite; open it from the tab Filters."""
    pull_request_project(github, bob)
    page = signed_in
    page.goto(
        f"{site}/projects/icalendar/pull-requests/"
        "?col=labels~not~present~needs+review&col=status~applies~open"
    )
    expect(page.locator("[data-pull-request]")).to_have_count(3)  # open, or without the label
    page.get_by_role("link", name="Save", exact=True).click()
    expect(page.get_by_role("link", name="Filters")).to_have_attribute("aria-current", "page")
    page.locator("[data-opposite]").get_by_role("link", name="Use it").click()
    expect(page.locator("[data-condition-row='0']")).to_contain_text(
        "It does not have the label needs review"
    )
    expect(page.locator("[data-opposite]")).to_have_count(0)
    status = page.locator("[data-condition-row='1']")
    status.locator("label.switch").click()  # off: grayed out
    expect(status.locator(".condition-name")).to_have_css("opacity", "0.45")
    status.locator("label.switch").click()  # on again
    expect(status.locator(".condition-name")).to_have_css("opacity", "1")
    page.get_by_label("Name").fill("Waiting")
    page.get_by_label("Description", exact=True).fill("Not *reviewed* yet")
    page.get_by_role("button", name="Save the filter").click()
    expect(page.get_by_text("The filter Waiting is saved.")).to_be_visible()
    item = page.locator("[data-filter='Waiting']")
    expect(item.locator("em")).to_have_text("reviewed")
    held = []  # the numbers wait until the spinner is seen
    page.route(re.compile(r"/filters/\d+/\?numbers=1$"), lambda route: held.append(route))
    item.locator("summary").click()  # the table of conditions, its numbers filled in
    expect(item.locator("[data-filter-conditions] tr[data-condition-count]")).to_have_count(2)
    expect(item.locator("[data-count-of='0'] .loading[role=status]")).to_be_visible()
    while not held:
        page.wait_for_timeout(20)
    held[0].continue_()
    expect(item.locator("[data-count-of='0']")).to_have_text("2")  # without the label
    expect(item.locator("[data-filter-total]")).to_have_text("The filter shows 3 pull requests.")
    item.get_by_role("link", name="Pull requests").click()
    expect(page.get_by_role("heading", name="Waiting: 3 pull requests")).to_be_visible()
    page.get_by_role("link", name="Save", exact=True).click()
    expect(page.get_by_role("button", name="Save Waiting")).to_be_hidden()  # it saves itself
    expect(page.locator("[data-save-status]")).not_to_have_attribute("hidden", "")
    page.get_by_role("link", name="← Back to the pull requests").click()
    expect(page.get_by_role("heading", name="Waiting: 3 pull requests")).to_be_visible()
    page.get_by_role("link", name="Filters", exact=True).click()
    page.get_by_role("link", name="New filter").click()  # the table, its menu + open
    expect(page.locator("[data-add-condition]")).to_have_attribute("open", "")
    expect(page.get_by_role("heading", name="Waiting")).to_have_count(0)


def test_steps_of_pull_requests(signed_in, site, github, bob):
    """Filters become steps without a new page, are moved in the bar, and are explained."""
    from pycal_dashboard.models import PullRequestFilter

    project = pull_request_project(github, bob)
    for name, column in (
        ("Conflicts", "branch~applies~conflict"),
        ("Review", "labels~applies~present~needs review"),
    ):
        PullRequestFilter.objects.create(project=project, name=name, columns=[column])
    page = signed_in
    page.goto(f"{site}/projects/icalendar/filters/")
    for name in ("Conflicts", "Review"):
        item = page.locator(f"[data-filter='{name}']")
        url = page.url
        item.get_by_role("button", name="Make it a step").click()
        expect(item.locator("[data-step-link]")).to_have_text(f"Step: {name}")
        assert page.url == url  # no new page
    page.get_by_role("link", name="Steps", exact=True).click()
    bar = page.locator("[data-step-bar]")
    expect(bar.locator("[data-step]")).to_have_count(2)
    expect(bar.locator("[data-step]").first).to_contain_text("Conflicts")
    bar.locator("[data-step]").nth(1).get_by_role("button", name="Move left: earlier").click()
    expect(bar.locator("[data-step]").first).to_contain_text("Review")
    expect(bar.locator("[data-step]").first.locator(".step-number")).to_have_text("Step 1")
    # the arrows to move: left of the name and right of it; disabled at the ends
    first = bar.locator("[data-step]").first
    expect(first.get_by_role("button", name="Move left: earlier")).to_be_disabled()
    expect(
        bar.locator("[data-step]").last.get_by_role("button", name="Move right: later")
    ).to_be_disabled()
    left = first.get_by_role("button", name="Move left: earlier").bounding_box()
    assert left["x"] < first.locator(".step-name").bounding_box()["x"]
    page.reload()
    expect(page.locator("[data-step-bar] [data-step]").first).to_contain_text("Review")
    heads = page.locator("[data-step-bar] [data-step]")
    heads.nth(1).drag_to(heads.nth(0))
    expect(page.locator("[data-step-bar] [data-step]").first).to_contain_text("Conflicts")
    # a click on a step shows it below; its condition is explained with the pencil
    page.locator("[data-step-bar]").get_by_role("link", name="Review").click()
    detail = page.locator("[data-step-detail]")
    detail.get_by_label("Name", exact=True).fill("Waiting for a review")
    detail.locator(".condition-edit > summary").click()
    detail.get_by_label("Summary", exact=True).last.fill("A person reviews it")
    description = detail.get_by_label("Description: how to do it")
    description.fill("Ask @")
    editor = detail.locator("[data-markdown-field]:has(#description-0)")
    editor.get_by_text("Variables", exact=True).click()  # the menu of the bar of the editor
    editor.get_by_role("menuitem", name="{author_handle}").click()  # inserted, no button
    expect(description).to_have_value("Ask @{author_handle}")
    expect(editor.locator("[data-variables-menu]")).not_to_have_attribute("open", "")
    # it saves itself: no button, a status that says so
    expect(detail.get_by_role("button", name="Save the step")).to_be_hidden()
    expect(detail.locator("[data-save-status]")).to_have_text("✓ Saved", timeout=10000)
    expect(page.locator("[data-step-bar]")).to_contain_text("Waiting for a review")
    # Preview: the text with an example pull request, said above it
    editor.get_by_role("button", name="Preview").click()
    shown = editor.locator("[data-markdown-shown]")
    expect(shown).to_contain_text("Ask @niccokunzmann")
    expect(shown).to_contain_text("With an example pull request:")
    page.reload()
    expect(page.locator("[data-step-detail]").get_by_label("Name", exact=True)).to_have_value(
        "Waiting for a review"
    )


def test_the_page_of_a_pull_request(page, site, github, bob):
    """From the table to a pull request: the bar of its steps, a click on a step, its tasks."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    for position, (name, column, summary) in enumerate(
        (
            ("Conflicts", "branch~applies~conflict", "Solve the conflict"),
            ("Review", "labels~applies~present~needs review", "Review it, {author_handle}"),
        )
    ):
        saved = PullRequestFilter.objects.create(project=project, name=name, columns=[column])
        PullRequestStep.objects.create(
            project=project,
            filter=saved,
            name=name,
            position=position,
            conditions={column: {"summary": summary, "description": "See *the guide*."}},
        )
    page.set_viewport_size({"width": 390, "height": 800})  # a phone
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_role("link", name="Ready", exact=True).click()
    bar = page.locator("[data-progress]")
    expect(bar.locator("[data-step]")).to_have_count(2)
    expect(bar.locator("[data-step]").first).to_have_attribute("data-complete", "true")
    current = bar.locator("[data-current]")
    expect(current).to_contain_text("Review")
    expect(current.locator("a")).to_have_attribute("aria-current", "step")
    expect(current.locator(".square-todo")).to_have_css(
        "background-color", "rgb(163, 36, 47)"
    )  # red
    task = page.locator("[data-task='todo']")
    expect(task.locator("em")).to_have_text("the guide")  # open: its description shows
    expect(task).to_contain_text("Review it, octocat")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")  # fits a phone
    bar.get_by_role("link", name="Conflicts").click()
    done = page.locator("[data-task='done']")
    expect(done).to_contain_text("Solve the conflict")
    expect(done.locator("em")).to_be_hidden()  # closed
    done.locator("summary").click()
    expect(done.locator("em")).to_be_visible()


def test_columns_of_reviews_and_of_the_author(page, site, github, bob):
    """The menu + adds the reviews of a pull request and the ratio of its author."""
    project = pull_request_project(github, bob)
    github.add_review("collective/icalendar", 1)
    github.add_review("collective/icalendar", 1, state="COMMENTED")  # not counted
    from pycal_dashboard.services.repository_update import RepositoryUpdate

    assert RepositoryUpdate(project.repositories.get()).run()
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_label("Add a condition").click()
    menu = page.locator("[data-add-condition] [data-condition-form]")
    menu.get_by_label("Condition").select_option("reviews")
    expect(menu.get_by_label("Name of the label")).to_be_hidden()
    expect(menu.get_by_label("The pull request has")).to_have_value("at_least")  # by default
    menu.get_by_label("Reviews", exact=True).fill("1")
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=reviews~all~at_least~1"))
    ready = page.locator("[data-pull-request='collective/icalendar#1']")
    expect(ready.locator(".col-condition")).to_contain_text("1 review")
    page.get_by_label("Add a condition").click()
    menu.get_by_label("Condition").select_option("author")
    menu.get_by_label("Of the author, in the project").select_option("review_ratio")
    expect(menu.get_by_label("Is", exact=True)).to_have_value("below")  # by default
    menu.get_by_label("Is", exact=True).select_option("above")
    menu.get_by_label("The number to compare with").fill("0.3")
    menu.get_by_role("button", name="Add the column").click()
    expect(page).to_have_url(re.compile(r"col=author~all~review_ratio~above~0.3"))
    # octocat opened 3 and reviewed once: 0.33
    expect(ready.locator(".col-condition").nth(1)).to_contain_text("0.33")
    expect(ready.locator(".col-condition").nth(1)).to_have_attribute("data-result", "yes")


def test_hide_a_step_and_check_the_pull_requests_outside(signed_in, site, github, bob):
    """The switch hides a step at once; Check lists the pull requests outside of the steps."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Conflicts", columns=["branch~applies~conflict"]
    )
    step = PullRequestStep.objects.create(project=project, filter=saved, name="Conflicts")
    page = signed_in
    page.goto(f"{site}/projects/icalendar/steps/")
    switch = page.locator("[data-step-visible] input[role=switch]")
    expect(switch).to_be_checked()  # visible by default
    assert switch.bounding_box()["width"] < 60  # the switch as everywhere
    page.locator("[data-step-visible] label.switch").click()  # hidden
    expect(page.locator("[data-save-status]")).to_have_attribute("data-state", "saved")
    step.refresh_from_db()
    assert step.hidden
    page.get_by_label("Add the labels").last.fill("conflict solved, done")  # on completing
    expect(page.locator("[data-save-status]")).to_have_attribute("data-state", "saved")
    step.refresh_from_db()
    assert step.actions["complete"]["add"] == ["conflict solved", "done"]
    page.get_by_role("link", name="Check").click()
    expect(page.get_by_role("heading", name="Outside of the steps")).to_be_visible()
    expect(page.locator("[data-outside-pull]")).to_have_count(2)  # Ready and Behind
    page.locator("[data-outside-pull='collective/icalendar#1'] a").first.click()
    expect(page.locator("[data-outside-note]")).to_be_visible()
    expect(page.locator("[data-progress] [data-step]")).to_have_count(0)  # hidden


def test_a_form_sent_while_the_site_starts_comes_back(signed_in, site, github, bob):
    """The page of the start waits for /health/ and then opens a page, never 405."""
    from pathlib import Path

    pull_request_project(github, bob)
    starting = (Path(__file__).parents[2] / "docker" / "starting.html").read_text()
    page = signed_in

    def restarting(route):  # nginx answers the form with the page of the start
        if route.request.method == "POST":
            route.fulfill(status=503, body=starting, content_type="text/html")
        else:
            route.continue_()

    page.route(re.compile(r"/projects/icalendar/update/$"), restarting)
    page.goto(f"{site}/projects/icalendar/")
    page.get_by_role("button", name="Update").click()
    expect(page.get_by_role("heading", name="The site is starting")).to_be_visible()
    # the update takes only POST: back to the page of the form, not 405
    expect(page).to_have_url(f"{site}/projects/icalendar/", timeout=10000)
    expect(page.get_by_role("heading", name="iCalendar")).to_be_visible()


def test_download_and_restore_a_backup(signed_in, site, github, bob, tmp_path):
    """The settings save the project as YAML and read it back."""
    from pycal_dashboard.models import PullRequestFilter

    project = pull_request_project(github, bob)
    PullRequestFilter.objects.create(project=project, name="Open", columns=["status~applies~open"])
    page = signed_in
    page.goto(f"{site}/projects/icalendar/settings/")
    with page.expect_download() as download:
        page.get_by_role("link", name="Download the backup").click()
    backup = tmp_path / "backup.yaml"
    download.value.save_as(backup)
    assert "dashboard_backup: 1" in backup.read_text()
    PullRequestFilter.objects.all().delete()
    page.locator("[data-restore]").get_by_label("A backup of a project").set_input_files(backup)
    page.get_by_label("Yes, replace the filters and steps").check()
    page.get_by_role("button", name="Restore the backup").click()
    expect(page.get_by_text("The backup is restored.")).to_be_visible()
    assert list(PullRequestFilter.objects.values_list("name", flat=True)) == ["Open"]


def test_the_message_of_the_pull_requests(signed_in, site, github, bob):
    """The flow of the message: none yet, edit, review the examples, the scope, saved."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestMessage, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Review")
    page = signed_in
    page.goto(f"{site}/projects/icalendar/pull-requests/")
    page.get_by_role("link", name="PR Message").click()
    expect(page.locator("[data-no-message]")).to_be_visible()
    page.get_by_role("link", name="Create the message").click()  # 2. edit
    page.get_by_role("textbox", name="The message").fill("**{pr_title}**: {tasks_todo}")
    page.get_by_role("button", name="Next: review →").click()  # 3. review
    label = page.locator("[data-example-label]")
    expect(label).to_have_text("Example 1 of 2: Review, 0 of 1 tasks done")
    expect(page.locator("[data-message-rendered] strong")).to_be_visible()
    page.get_by_role("link", name="The next example: one more task done").click()
    expect(label).to_have_text("Example 2 of 2: outside of the steps, 1 of 1 tasks done")
    expect(page.locator("[data-message-rendered]")).to_contain_text("Nothing to do.")
    page.get_by_role("textbox", name="The message of the pull request").fill("1")
    page.get_by_role("button", name="Show").click()
    expect(page.locator("[data-message-rendered]")).to_contain_text("Ready")
    page.get_by_role("link", name="Edit this step").click()  # the step, and back
    page.get_by_role("link", name="← Back to the review of the message").click()
    expect(page.locator("[data-message-rendered]")).to_contain_text("Ready")
    page.get_by_role("link", name="Next: scope →").click()  # 4. scope
    save = page.locator("[data-save-message]")
    expect(save).to_have_text("Update 0 pull requests")  # off by default
    page.locator("[data-message-scope]").get_by_text("Add to all open pull requests").click()
    expect(save).to_have_text("Update 3 pull requests")
    page.set_viewport_size({"width": 390, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")  # fits a phone
    save.click()
    expect(page.get_by_text("The message is saved: 3 pull requests get it")).to_be_visible()
    message = PullRequestMessage.objects.get()
    assert message.to_open and message.template.startswith("**{pr_title}**")


def test_a_filter_keeps_its_name_from_the_step_to_the_table_and_back(signed_in, site, github, bob):
    """Step -> Edit the filter -> the table -> change a condition -> Save: still the filter."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Review")
    PullRequestFilter.objects.create(project=project, name="Other", columns=[])
    page = signed_in
    page.goto(f"{site}/projects/icalendar/steps/")
    page.get_by_role("link", name="Edit the filter").click()
    expect(page.get_by_label("Name", exact=True)).to_have_value("Review")
    page.get_by_role("link", name="← Back to the pull requests").click()
    page.locator("th.col-condition .column-menu summary").first.click()  # the gear
    menu = page.locator("th.col-condition [data-condition-form]").first
    menu.get_by_label("Name of the label").fill("needs docs")
    menu.get_by_role("button", name="Change the column").click()
    expect(page.get_by_role("heading", name=re.compile("^Review: "))).to_be_visible()
    page.get_by_role("link", name="Save", exact=True).click()
    expect(page.get_by_label("Name", exact=True)).to_have_value("Review")  # not empty
    page.get_by_label("Name", exact=True).fill("Other")  # the name of another filter
    page.get_by_role("button", name="Save as a new filter").click()
    expect(page.locator("[data-conflict]")).to_contain_text("The project has a filter Other")
    page.get_by_role("button", name="Replace Other").click()
    expect(page.get_by_text("The filter Other is saved.")).to_be_visible()
    assert PullRequestFilter.objects.get(name="Other").columns == [
        "labels~applies~present~needs docs"
    ]


def test_a_saved_filter_saves_itself(signed_in, site, github, bob):
    """The page of a saved filter: saved while it is edited, linked to its conditions and step."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    step = PullRequestStep.objects.create(project=project, filter=saved, name="Peer review")
    page = signed_in
    page.goto(f"{site}/projects/icalendar/filters/")
    page.locator("[data-filter='Review']").get_by_role("link", name="Edit").click()
    expect(page.get_by_role("button", name="Save Review")).to_be_hidden()
    page.get_by_label("Name", exact=True).fill("Maintainer review")
    status = page.locator("[data-save-status]")
    expect(status).to_have_text("✓ Saved", timeout=10000)
    saved.refresh_from_db()
    assert saved.name == "Maintainer review"
    page.get_by_role("link", name="Step: Peer review").click()
    expect(page.locator(f"[data-step-detail='{step.pk}']")).to_be_visible()
    page.go_back()
    page.get_by_role("link", name="Edit the conditions").click()
    expect(page.get_by_role("heading", name=re.compile("^Maintainer review"))).to_be_visible()


def test_saving_as_a_new_filter_leaves_the_saved_one(signed_in, site, github, bob):
    from pycal_dashboard.models import PullRequestFilter

    project = pull_request_project(github, bob)
    PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    page = signed_in
    page.goto(f"{site}/projects/icalendar/filters/")
    page.locator("[data-filter='Review']").get_by_role("link", name="Edit").click()
    page.get_by_label("Name", exact=True).fill("Copy")
    page.get_by_role("button", name="Save as a new filter").click()
    expect(page.get_by_text("The filter Copy is saved.")).to_be_visible()
    names = sorted(PullRequestFilter.objects.values_list("name", flat=True))
    assert names == ["Copy", "Review"]


def test_readers_go_from_the_filters_to_the_steps_and_back(page, site, github, bob):
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project, name="Review", columns=["labels~applies~present~needs review"]
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Peer review")
    page.goto(f"{site}/projects/icalendar/filters/")
    page.get_by_role("link", name="Step: Peer review").click()
    page.get_by_role("link", name="Filter: Review").click()
    expect(page.get_by_role("heading", name=re.compile("^Review"))).to_be_visible()


def test_the_evidence_of_a_task_and_the_page_of_its_author(page, site, github, bob):
    """A task links to the merge box on GitHub and to the page of the author with its tabs."""
    from pycal_dashboard.models import PullRequestFilter, PullRequestStep

    project = pull_request_project(github, bob)
    saved = PullRequestFilter.objects.create(
        project=project,
        name="Ready",
        columns=["branch~applies~conflict", "author~applies~review_ratio~below~1"],
    )
    PullRequestStep.objects.create(project=project, filter=saved, name="Ready")
    page.goto(f"{site}/projects/icalendar/pull/2/")
    tasks = page.locator("[data-tasks]")
    expect(tasks.get_by_role("link", name="Where it is merged, on GitHub")).to_have_attribute(
        "href", "https://github.com/collective/icalendar/pull/2#issue-comment-box"
    )
    tasks.get_by_role("link", name="octocat in the project").click()
    states = page.locator("[data-contributor-states]")
    expect(states).to_contain_text("Review to pull request ratio")
    expect(states).to_contain_text("Pull requests opened")
    page.get_by_role("link", name="Pull requests 3").click()
    items = page.locator("[data-contributor-list='pull-requests'] li")
    expect(items).to_have_count(3)
    page.get_by_role("link", name="#2 Conflict").click()
    expect(page.locator("[data-tasks]")).to_be_visible()
