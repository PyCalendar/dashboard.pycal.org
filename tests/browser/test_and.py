"""Join conditions by AND on the page of saving a filter: drag and drop, and where they land."""

import re

from playwright.sync_api import expect

from .test_projects import pull_request_project

LABEL = "labels~applies~present~needs+review"
OPEN = "status~applies~open"
CONFLICT = "branch~applies~conflict"


def open_page(page, site, *columns):
    page.goto(f"{site}/projects/icalendar/filters/save/?" + "&".join(f"col={c}" for c in columns))
    return page.locator("tbody[data-section='checks']")


def hold(page, source, target):
    """Pick up a row and hold it over a target, as before a drop."""
    source.hover()
    page.mouse.down()
    box = target.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=5)
    page.mouse.move(box["x"] + box["width"] / 2 + 2, box["y"] + box["height"] / 2, steps=2)


def test_join_two_conditions_by_dragging_and_take_one_out(signed_in, site, github, bob):
    """A condition dropped onto another one makes an AND; dropped between two, it leaves it."""
    pull_request_project(github, bob)
    page = signed_in
    checks = open_page(page, site, LABEL, CONFLICT, OPEN)
    page.get_by_label("Name").fill("Typed")
    checks.locator("tr[data-condition-row='2']").drag_to(
        checks.locator("tr[data-condition-row='0']")
    )
    expect(page).to_have_url(re.compile(r"col=and1~labels.*col=and1~status~applies~open"))
    head = checks.locator("tr[data-and-head]")
    expect(head).to_contain_text("All of these, as one condition:")
    expect(head).to_contain_text("It has the label needs review and it is open")
    expect(checks.locator("tr.and-member")).to_have_count(2)
    expect(page.get_by_label("Name")).to_have_value("Typed")  # what was typed stays
    # out of the AND: between the two conditions that are left
    member = checks.locator("tr.and-member", has_text="It is open")
    member.drag_to(checks.locator("tr[data-gap]").last)
    expect(checks.locator("tr.and-member")).to_have_count(0)
    expect(checks.locator("tr[data-condition-row]").last).to_contain_text("It is open")


def test_where_a_dragged_condition_lands_is_highlighted(signed_in, site, github, bob):
    """The AND as a whole, a single condition, or the gap in between; not where it was."""
    pull_request_project(github, bob)
    page = signed_in
    checks = open_page(page, site, f"and1~{LABEL}", f"and1~{OPEN}", CONFLICT)
    single = checks.locator("tr[data-condition-row='2']")
    gaps = checks.locator("tr[data-gap]")
    expect(gaps).to_have_count(3)  # before the AND, before the single one, at the end
    hold(page, single, checks.locator("tr.and-member").first)
    and_rows = checks.locator("tr[data-and-head], tr.and-member")
    for number in range(3):  # its head and both conditions
        expect(and_rows.nth(number)).to_have_class(re.compile("join-target"))
    expect(single).not_to_have_class(re.compile("join-target"))
    assert gaps.first.bounding_box()["height"] >= 16  # room to drop in between
    box = gaps.first.bounding_box()
    page.mouse.move(box["x"] + 20, box["y"] + box["height"] / 2, steps=3)
    expect(gaps.first).to_have_class(re.compile("gap-target"))
    expect(and_rows.first).not_to_have_class(re.compile("join-target"))
    # the gaps next to itself: it would stay where it is, so nothing is highlighted
    box = gaps.nth(1).bounding_box()
    page.mouse.move(box["x"] + 20, box["y"] + box["height"] / 2, steps=3)
    expect(gaps.nth(1)).not_to_have_class(re.compile("gap-target"))
    page.mouse.up()
    member = checks.locator("tr.and-member").first
    hold(page, member, single)  # a single condition: a new AND
    expect(single).to_have_class(re.compile("join-target"))
    page.mouse.up()


def test_a_drop_where_it_was_picked_up_changes_nothing(signed_in, site, github, bob):
    pull_request_project(github, bob)
    page = signed_in
    checks = open_page(page, site, LABEL, CONFLICT, OPEN)
    address = page.url
    row = checks.locator("tr[data-condition-row='1']")
    for target in (
        row,
        checks.locator("tr[data-gap]").nth(1),
        checks.locator("tr[data-gap]").nth(2),
    ):
        row.drag_to(target)
        page.wait_for_timeout(300)
        assert page.url == address  # no page came
    expect(checks.locator("tr[data-condition-row]")).to_have_count(3)
    names = checks.locator("tr[data-condition-row] td.condition-name")
    expect(names.nth(1)).to_contain_text("conflict")
