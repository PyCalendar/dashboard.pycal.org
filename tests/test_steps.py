"""The steps of pull requests: made of filters, ordered, explained, and where a pull request is."""

import re

import pytest

from pycal_dashboard.models import Issue, PullRequestFilter, PullRequestStep, Repository
from pycal_dashboard.services.project_editor import ProjectEditor
from pycal_dashboard.services.repository_update import RepositoryUpdate
from pycal_dashboard.services.step_assignment import StepAssignment
from pycal_dashboard.step_template import escape, expand

pytestmark = pytest.mark.django_db
REPO = "collective/icalendar"
JSON = {"HTTP_ACCEPT": "application/json"}


@pytest.fixture
def project(github, bob):
    github.add_repository(REPO, installation=11)
    github.add_label(REPO, "needs review", "", "fbca04")
    github.add_issue(REPO, "Ready", pull_request=True, labels=("needs review",))
    github.add_issue(REPO, "Conflict", pull_request=True, mergeable_state="dirty")
    github.add_issue(REPO, "Merged", pull_request=True, state="closed", merged=True)
    repository = Repository.objects.create(full_name=REPO)
    project = ProjectEditor.create(bob, "iCalendar", slug="icalendar")
    project.repositories.add(repository)
    assert RepositoryUpdate(repository).run()
    return project


@pytest.fixture
def filters(project):
    conflict = PullRequestFilter.objects.create(
        project=project, name="Conflicts", columns=["branch~applies~conflict"]
    )
    review = PullRequestFilter.objects.create(
        project=project,
        name="Review",
        columns=["labels~applies~present~needs review", "status~all~open"],
    )
    return conflict, review


def make_step(client, saved):
    return client.post("/projects/icalendar/steps/add/", {"filter": saved.pk})


def test_no_steps_yet(client, project):
    page = client.get("/projects/icalendar/steps/").content.decode()
    assert "data-no-steps" in page and 'href="/projects/icalendar/filters/"' in page
    tabs = page.split('<ul class="tabs">')[1].split("</ul>")[0]
    assert tabs.index("Filters") < tabs.index("Steps")


def test_make_a_filter_a_step(client, project, filters, bob):
    conflict, review = filters
    client.force_login(bob)
    answer = make_step(client, conflict)
    step = PullRequestStep.objects.get()
    assert answer["Location"] == f"/projects/icalendar/steps/?step={step.pk}"
    assert (step.name, step.filter, step.position) == ("Conflicts", conflict, 0)
    answer = client.post("/projects/icalendar/steps/add/", {"filter": review.pk}, **JSON)
    assert answer.status_code == 201 and answer.json()["name"] == "Review"
    assert PullRequestStep.objects.get(filter=review).position == 1
    answer = make_step(client, conflict)
    assert answer.status_code == 409 and "The filter is a step already" in answer.content.decode()


def test_the_filters_page_makes_steps(client, project, filters, bob):
    conflict, review = filters
    client.force_login(bob)
    make_step(client, conflict)
    page = client.get("/projects/icalendar/filters/").content.decode()
    item = page.split('data-filter="Conflicts"')[1].split("</li>")[0]
    assert "data-step-link" in item and "Step: Conflicts" in item
    item = page.split('data-filter="Review"')[1].split("data-filter-details")[0]
    assert "data-make-step" in item and "Make it a step" in item


def test_only_writers_change_steps(client, project, filters, alice):
    conflict, _review = filters
    assert make_step(client, conflict).status_code == 302  # sign in first
    assert not PullRequestStep.objects.exists()
    client.force_login(alice)
    assert make_step(client, conflict).status_code == 403


def test_the_bar_and_moving_steps(client, project, filters, bob):
    conflict, review = filters
    client.force_login(bob)
    make_step(client, conflict)
    make_step(client, review)
    first, second = PullRequestStep.objects.all()
    page = client.get("/projects/icalendar/steps/").content.decode()
    bar = page.split("data-step-bar>")[1].split("</ol>")[0]
    assert bar.index("Conflicts") < bar.index("Review")
    assert "Step 1" in bar and "Step 2" in bar and 'draggable="true"' in bar
    client.post(f"/projects/icalendar/steps/{second.pk}/move/", {"direction": "left"})
    assert list(PullRequestStep.objects.values_list("name", flat=True)) == ["Review", "Conflicts"]
    answer = client.post(f"/projects/icalendar/steps/{second.pk}/move/", {"to": "1"}, **JSON)
    assert answer.status_code == 204
    assert list(PullRequestStep.objects.values_list("name", flat=True)) == ["Conflicts", "Review"]


def test_edit_a_step_and_its_conditions(client, project, filters, bob):
    _conflict, review = filters
    client.force_login(bob)
    make_step(client, review)
    step = PullRequestStep.objects.get()
    page = client.get(f"/projects/icalendar/steps/?step={step.pk}").content.decode()
    detail = page.split("data-step-detail")[1]
    assert "PR has the label needs review" in detail
    assert "PR is open" not in detail  # off: no part of the filter
    assert "✎" not in detail and detail.count("data-variables-menu") == 2  # summary, condition
    assert f'data-markdown-preview="/projects/icalendar/steps/{step.pk}/preview/"' in detail
    assert "tutorial/projects.html#step-variables" in detail  # the documentation, no list
    assert "variables-help" not in detail
    assert (
        'role="menuitem" data-variable="{author_mention}"' in detail
        and "Insert</button>" not in detail
    )
    assert '<textarea id="description-0" name="description-0"' in detail  # the editor
    client.post(
        f"/projects/icalendar/steps/{step.pk}/edit/",
        {
            "name": "Waiting for a review",
            "summary": "Thanks, {author_mention}! Waiting for {project_name}.",
            "value-0": "labels~applies~present~needs review",
            "summary-0": "A person reviews it",
            "description-0": "See [the guide](https://docs.example.org/) for {repository_full_name}.",
        },
    )
    step.refresh_from_db()
    assert step.name == "Waiting for a review"
    notes = step.conditions["labels~applies~present~needs review"]
    assert notes["summary"] == "A person reviews it"
    page = client.get(f"/projects/icalendar/steps/?step={step.pk}").content.decode()
    assert "With an example pull request" not in page  # only the button Preview shows it
    preview = client.post(
        f"/projects/icalendar/steps/{step.pk}/preview/", {"text": step.summary}
    ).content.decode()
    assert "Thanks, @niccokunzmann! Waiting for iCalendar." in preview
    assert "With an example pull request:" in preview  # it has variables
    plain = client.post(f"/projects/icalendar/steps/{step.pk}/preview/", {"text": "*Just* {x}"})
    assert plain.content.decode() == "<p><em>Just</em> {x}</p>"  # Markdown as it is
    client.logout()
    page = client.get(f"/projects/icalendar/steps/?step={step.pk}").content.decode()
    assert "data-edit-step" not in page and "A person reviews it" in page  # public, read only
    assert "Thanks, @niccokunzmann! Waiting for iCalendar." in page  # with the examples
    assert 'href="https://docs.example.org/"' in page and "collective/icalendar" in page


def test_remove_a_step_keeps_its_filter(client, project, filters, bob):
    conflict, _review = filters
    client.force_login(bob)
    make_step(client, conflict)
    step = PullRequestStep.objects.get()
    client.post(f"/projects/icalendar/steps/{step.pk}/remove/")
    assert not PullRequestStep.objects.exists() and PullRequestFilter.objects.filter(pk=conflict.pk)
    assert client.get("/projects/icalendar/steps/?step=99").status_code == 404


def test_a_pull_request_is_in_the_left_most_step_that_applies(project, filters):
    conflict, review = filters
    PullRequestStep.objects.create(project=project, filter=review, name="Review", position=0)
    PullRequestStep.objects.create(project=project, filter=conflict, name="Conflicts", position=1)
    steps = StepAssignment(project)
    pulls = {i.title: i for i in Issue.objects.select_related("pull_state", "repository")}
    assert steps.step_of(pulls["Ready"]).name == "Review"  # has the label
    assert steps.step_of(pulls["Conflict"]).name == "Conflicts"
    assert steps.step_of(pulls["Merged"]) is None  # no condition applies
    PullRequestStep.objects.filter(name="Conflicts").update(position=0)
    PullRequestStep.objects.filter(name="Review").update(position=1)
    assert StepAssignment(project).step_of(pulls["Ready"]).name == "Review"


def test_templates_are_safe_for_the_input_of_others():
    """A title of anybody stays text: no links, images or HTML of its own."""
    from pycal_dashboard.markdown_text import render

    values = {"pr_title": "[click](https://evil.example) ![x](https://evil.example/x.png) <b>"}
    html = render(expand("Title: {pr_title} {unknown} {pr_title.upper}", values))
    assert "<a " not in html and "<img" not in html and "<b>" not in html
    assert "{unknown}" in html and "{pr_title.upper}" in html  # nothing else is evaluated
    assert escape("a\nb") == "a b"


def test_a_step_saves_itself_for_the_script(client, project, filters, bob):
    _conflict, review = filters
    client.force_login(bob)
    make_step(client, review)
    step = PullRequestStep.objects.get()
    answer = client.post(f"/projects/icalendar/steps/{step.pk}/edit/", {"name": "Wait"}, **JSON)
    assert answer.status_code == 200 and answer.json() == {
        "step": step.pk,
        "name": "Wait",
        "color": "",
    }
    page = client.get(f"/projects/icalendar/steps/?step={step.pk}").content.decode()
    assert "data-save-status" in page and 'data-saving="Saving…"' in page


def test_the_variables_are_grouped_and_documented_with_examples():
    """Every variable is in its group, with an example, in the code and in the docs."""
    from pathlib import Path

    from pycal_dashboard.step_template import GROUPS, VARIABLES

    docs = (Path(__file__).parent.parent / "docs" / "tutorial" / "projects.rst").read_text()
    for _key, (title, members) in GROUPS.items():
        assert f".. list-table:: {title}" in docs
        for name, (_meaning, example) in members.items():
            assert f"``{{{name}}}``" in docs, name
            for line in example.split("\n"):  # an example of several lines: each line
                assert f"``{line}``" in docs, name
    assert {"author_mention", "author_name", "author_handle", "step_id"} <= set(VARIABLES)


def test_the_values_of_a_pull_request(project, filters):
    from pycal_dashboard.models import GitHubUser
    from pycal_dashboard.step_template import values_of

    _conflict, review = filters
    step = PullRequestStep.objects.create(project=project, filter=review, name="Review")
    GitHubUser.objects.filter(login="octocat").update(name="The Octocat")
    pull = Issue.objects.select_related("author", "repository").get(title="Ready")
    values = values_of(pull, project, step)
    assert values["author_mention"] == "@octocat" and values["author_name"] == "The Octocat"
    assert values["author_handle"] == "octocat" and values["pr_number"] == "1"
    assert values["pr_merge_box"] == pull.url + "#partial-pull-merging"
    assert (values["step_name"], values["step_number"], values["step_id"]) == (
        "Review",
        "1",
        str(step.pk),
    )


def test_the_address_of_the_steps_of_a_pull_request(project, filters, settings):
    from pycal_dashboard.step_template import example, values_of

    settings.SITE_URL = "https://dashboard.example.org"
    pull = Issue.objects.select_related("author", "repository").get(title="Ready")
    url = values_of(pull, project)["pr_steps_url"]
    assert url == (
        "https://dashboard.example.org/projects/icalendar/pull/1/"
        "?repository=collective%2Ficalendar"  # always, also with one repository
    )
    assert example(project)["pr_steps_url"].endswith(
        "/projects/icalendar/pull/42/?repository=collective%2Ficalendar"
    )
    project.repositories.add(Repository.objects.create(full_name="collective/other"))
    assert values_of(pull, project)["pr_steps_url"] == url  # the same with another one


def test_a_step_hidden_in_the_page_of_a_pull_request(client, project, filters, bob):
    conflict, _review = filters
    client.force_login(bob)
    make_step(client, conflict)
    step = PullRequestStep.objects.get()
    page = client.get("/projects/icalendar/steps/").content.decode()
    assert 'name="visible" value="on" checked' in page  # visible by default
    assert "data-hidden-mark" not in page
    edit = f"/projects/icalendar/steps/{step.pk}/edit/"
    client.post(edit, {"name": "C", "visible_form": "1"}, **JSON)  # switched off
    step.refresh_from_db()
    assert step.hidden
    assert "data-hidden-mark" in client.get("/projects/icalendar/steps/").content.decode()
    client.post(edit, {"name": "C"}, **JSON)  # a form without the switch keeps it
    step.refresh_from_db()
    assert step.hidden
    client.post(edit, {"name": "C", "visible_form": "1", "visible": "on"}, **JSON)
    step.refresh_from_db()
    assert not step.hidden


def test_a_step_has_a_color_and_a_button_to_edit_its_filter(client, project, filters, bob):
    conflict, _review = filters
    client.force_login(bob)
    make_step(client, conflict)
    step = PullRequestStep.objects.get()
    edit = f"/projects/icalendar/steps/{step.pk}/edit/"
    client.post(edit, {"name": "C", "color": "#bbf7d0"}, **JSON)
    step.refresh_from_db()
    assert step.color == "#bbf7d0"
    page = client.get("/projects/icalendar/steps/").content.decode()
    assert 'style="--step-color: #bbf7d0"' in page
    assert 'name="color" value="#bbf7d0" checked' in page
    edit_filter = page.split(" data-edit-filter")[0].rsplit('href="', 1)[1]
    assert edit_filter.startswith("/projects/icalendar/filters/save/?col=branch")
    assert edit_filter.endswith(f'saved={conflict.pk}"')
    client.post(edit, {"name": "C", "color": "red; background: url(x)"}, **JSON)
    step.refresh_from_db()
    assert step.color == ""  # only the colors of the palette


def test_check_lists_the_pull_requests_outside_of_the_steps(client, project, filters):
    conflict, _review = filters
    page = client.get("/projects/icalendar/steps/").content.decode()
    assert "data-check-steps" not in page  # no steps: nothing to check
    PullRequestStep.objects.create(project=project, filter=conflict, name="Conflicts")
    page = client.get("/projects/icalendar/steps/").content.decode()
    assert 'href="/projects/icalendar/steps/check/" data-check-steps' in page
    check = client.get("/projects/icalendar/steps/check/").content.decode()  # public
    outside = re.findall(r'data-outside-pull="([^"]+)"', check)
    assert outside == [f"{REPO}#1"]  # Ready: open and without a conflict; not the merged one
    assert "1 pull request is outside of the steps." in check
    every = client.get("/projects/icalendar/steps/check/?all=1").content.decode()
    assert sorted(re.findall(r'data-outside-pull="([^"]+)"', every)) == [f"{REPO}#1", f"{REPO}#3"]
    assert '/projects/icalendar/pull/1/badge.svg"' in check


def test_check_without_steps(client, project):
    assert "data-no-steps" in client.get("/projects/icalendar/steps/check/").content.decode()


def test_readers_see_the_visible_steps_and_their_filters(client, project, filters, bob):
    """Who only reads the project sees the steps that are visible, linked to their filters."""
    conflict, review = filters
    client.force_login(bob)
    make_step(client, conflict)
    make_step(client, review)
    hidden, visible = PullRequestStep.objects.order_by("position")
    PullRequestStep.objects.filter(pk=hidden.pk).update(hidden=True)
    assert "Conflicts" in client.get("/projects/icalendar/steps/").content.decode()
    client.logout()
    page = client.get("/projects/icalendar/steps/").content.decode()
    assert f'data-step="{visible.pk}"' in page and f'data-step="{hidden.pk}"' not in page
    assert "Conflicts" not in page  # the first visible one is shown
    link = page.split(" data-filter-link")[0].rsplit('href="', 1)[1]
    assert link.startswith("/projects/icalendar/pull-requests/?col=labels")
    assert link.endswith(f'saved={review.pk}"')
    page = client.get(f"/projects/icalendar/steps/?step={hidden.pk}").content.decode()
    assert "Conflicts" not in page and f'data-step-detail="{visible.pk}"' in page
    filters_page = client.get("/projects/icalendar/filters/").content.decode()
    assert f'?step={visible.pk}" data-step-link' in filters_page
    assert f'?step={hidden.pk}" data-step-link' not in filters_page
    assert "data-make-step" not in filters_page and "data-edit-filter" not in filters_page


def test_a_step_by_its_id_and_one_that_was_removed(client, project, filters, bob):
    """Labels on GitHub link ?step_id=; a removed step shows a notice and the other steps."""
    conflict, review = filters
    client.force_login(bob)
    make_step(client, conflict)
    make_step(client, review)
    first, second = PullRequestStep.objects.order_by("position")
    page = client.get(f"/projects/icalendar/steps/?step_id={second.pk}").content.decode()
    assert f'data-step-detail="{second.pk}"' in page and "data-missing-step" not in page
    removed = second.pk
    second.delete()
    answer = client.get(f"/projects/icalendar/steps/?step_id={removed}")
    page = answer.content.decode()
    assert answer.status_code == 404 and "data-missing-step" in page
    assert f"The project has no step {removed}: it may have been removed." in page
    assert f'data-step-detail="{first.pk}"' in page  # the steps it has
    answer = client.get("/projects/icalendar/steps/?step_id=nothing")
    assert answer.status_code == 404 and "data-missing-step" in answer.content.decode()


def test_readers_see_which_authors_a_step_skips(client, project, filters, bob):
    conflict, _review = filters
    client.force_login(bob)
    make_step(client, conflict)
    step = PullRequestStep.objects.get()
    step.skip_authors = ["niccokunzmann"]
    step.save()
    client.logout()
    page = client.get(f"/projects/icalendar/steps/?step_id={step.pk}").content.decode()
    shown = page.split("data-skip-authors")[1].split("</p>")[0]
    assert (
        "Skipped for the pull requests of" in shown and 'data-github-user="niccokunzmann"' in shown
    )
    checks, skips = page.index("<h3>Quality checks</h3>"), page.index("<h3>Skip conditions</h3>")
    assert checks < skips < page.index("data-skip-authors")  # below the quality checks


def test_the_skip_conditions_are_below_the_quality_checks(client, project, filters, bob):
    conflict, _review = filters
    client.force_login(bob)
    make_step(client, conflict)
    step = PullRequestStep.objects.get()
    page = client.get(f"/projects/icalendar/steps/?step_id={step.pk}").content.decode()
    checks, skips = page.index("<h3>Quality checks</h3>"), page.index("<h3>Skip conditions</h3>")
    assert checks < skips < page.index('name="skip_authors"') < page.index("<h3>Labels</h3>")
    assert "Tasks" not in page and "tasks" not in page.split("<main")[1]


def test_the_step_lists_its_conditions_of_skip_if(client, project, filters, bob):
    _conflict, review = filters
    review.columns = ["labels~applies~present~needs review", "status~skip~closed"]
    review.save()
    client.force_login(bob)
    make_step(client, review)
    step = PullRequestStep.objects.get()
    page = client.get(f"/projects/icalendar/steps/?step_id={step.pk}").content.decode()
    assert "Skipped if: PR is closed" in page
    tasks = page.split('class="step-conditions"')[1].split("</ul>")[0]
    assert "closed" not in tasks  # no task
    client.logout()
    assert "Skipped if: PR is closed" in client.get("/projects/icalendar/steps/").content.decode()


def test_the_merge_box_is_a_link_in_markdown(project):
    """Its value is escaped as text, and still an address in a link of Markdown."""
    from pycal_dashboard.markdown_text import render
    from pycal_dashboard.step_template import expand, values_of

    pull = Issue.objects.select_related("author", "repository").get(title="Ready")
    text = expand("[Merge it]({pr_merge_box})", values_of(pull, project))
    assert 'href="https://github.com/collective/icalendar/pull/1#partial-pull-merging"' in render(
        text
    )
