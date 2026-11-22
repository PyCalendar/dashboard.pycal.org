"""Descriptions that people type are Markdown: shown safely, edited with a bar and a preview."""

import re
from pathlib import Path

import pytest
from django.template import Context, Template

from pycal_dashboard.markdown_text import render
from pycal_dashboard.services.project_editor import ProjectEditor

TEMPLATES = Path(__file__).parent.parent / "pycal_dashboard" / "templates"
# the fields that people type to describe something: the model and the field
TYPED = {"project.description"}


@pytest.mark.parametrize(
    ("text", "html"),
    [
        ("**bold** and *italic*", "<p><strong>bold</strong> and <em>italic</em></p>"),
        ("- one\n- two", "<ul>\n<li>one</li>\n<li>two</li>\n</ul>"),
        ("1. one\n2. two", "<ol>\n<li>one</li>\n<li>two</li>\n</ol>"),
        ("> quoted", "<blockquote>\n<p>quoted</p>\n</blockquote>"),
        ("`code`", "<p><code>code</code></p>"),
        ("~~gone~~", "<p><s>gone</s></p>"),
        ("# Title", "<h1>Title</h1>"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_markdown_is_rendered(text, html):
    assert render(text) == html


def test_links_open_safely():
    html = render("[pycal](https://pycal.org)")
    assert 'href="https://pycal.org"' in html and 'rel="nofollow noopener noreferrer"' in html


@pytest.mark.parametrize(
    "text",
    [
        "<script>alert(1)</script>",
        '<img src="https://evil.example/x.png" onerror="alert(1)">',
        "[click](javascript:alert(1))",
        '<a href="https://x.example" onclick="alert(1)">x</a>',
        "![image](https://evil.example/x.png)",
        '<iframe src="https://evil.example"></iframe>',
        "<style>body { display: none }</style>",
    ],
)
def test_nothing_dangerous_or_from_other_sites(text):
    """No scripts, no handlers, no images or frames of other sites: raw HTML stays text."""
    html = render(text)
    assert not re.search(r"<(script|img|iframe|style)\b", html)  # escaped as text at most
    assert not re.search(r"<[^>]*\son\w+=", html)  # no handlers in a tag
    assert 'href="javascript' not in html


def test_the_filter_marks_markdown():
    html = Template("{% load markdown %}{{ text|markdown }}").render(Context({"text": "*hi*"}))
    assert html == "<p><em>hi</em></p>"
    assert Template("{% load markdown %}{{ text|markdown }}").render(Context({})) == ""


def test_typed_descriptions_are_shown_as_markdown():
    """Every template that shows a typed description passes it through |markdown."""
    for path in TEMPLATES.rglob("*.html"):
        text = path.read_text()
        for field in TYPED:
            for found in re.finditer(r"\{\{\s*" + re.escape(field) + r"(\|[^}]*)?\}\}", text):
                assert "markdown" in (found[1] or ""), (path.name, found[0])


def test_typed_descriptions_are_edited_with_the_bar():
    """A field named description is the partial of Markdown, never a bare text area."""
    for path in TEMPLATES.rglob("*.html"):
        if path.name == "_markdown_field.html":
            continue
        assert not re.search(r'<textarea[^>]*name="description"', path.read_text()), path.name


@pytest.mark.django_db
def test_a_project_shows_its_description_as_markdown(client, bob):
    project = ProjectEditor.create(
        bob, "iCalendar", "The **calendars** of [Python](https://python.org)"
    )
    page = client.get(project.path()).content.decode()
    assert "<strong>calendars</strong>" in page and 'href="https://python.org"' in page
    listed = client.get("/projects/").content.decode()
    assert "<strong>calendars</strong>" in listed
    assert client.get(project.path() + "x").status_code in (301, 404)
    assert client.get(f"/projects/{project.slug}.json").json()["description"].startswith("The **")


@pytest.mark.django_db
def test_the_form_has_the_bar_and_the_preview(client, bob):
    client.force_login(bob)
    page = client.get("/projects/new/").content.decode()
    assert "data-markdown-field" in page and '<markdown-toolbar for="description">' in page
    for button in ("md-bold", "md-italic", "md-link", "md-unordered-list", "md-ordered-list"):
        assert f"<{button}>" in page
    assert "vendor/markdown-toolbar-element-2.2.3.js" in page and "markdown-editor.js" in page
    assert 'data-markdown-preview="/markdown/preview/"' in page


@pytest.mark.django_db
def test_the_preview_renders_as_the_page(client, bob):
    assert client.post("/markdown/preview/", {"text": "*x*"}).status_code == 302  # sign in
    client.force_login(bob)
    answer = client.post("/markdown/preview/", {"text": "**x** <script>y</script>"})
    assert answer.content.decode() == "<p><strong>x</strong> &lt;script&gt;y&lt;/script&gt;</p>"
    assert client.get("/markdown/preview/").status_code == 405


def test_lists_of_tasks_show_checkboxes_as_on_github():
    """- [ ] and - [x] show a checkbox with the state, which cannot be changed."""
    from pycal_dashboard.markdown_text import render

    html = render("- [ ] to do\n- [x] done\n- [X] also done\n- no task\n\nnot [x] a task")
    assert html.count('<input type="checkbox" class="task-box" disabled>') == 1
    assert html.count('<input type="checkbox" class="task-box" disabled checked>') == 2
    assert html.count('<li class="task-item">') == 3 and "<li>no task</li>" in html
    assert "<p>not [x] a task</p>" in html  # only at the start of an item


def test_text_cannot_make_its_own_checkboxes():
    from pycal_dashboard.markdown_text import render

    html = render('<input type="checkbox" checked> <li>[x] raw</li>')
    assert "<input" not in html.replace("&lt;input", "")  # raw HTML stays text


def test_an_image_of_another_site_shows_its_text():
    """Such as a badge of insight.pycal.org in a message: seen where it is, but not loaded."""
    html = render(
        "[![Replies of Mrbozz](https://insight.pycal.org/badge/s/x/replies/Mrbozz.svg)]"
        "(https://insight.pycal.org/s/x/replies/Mrbozz/) ![](https://other.example/a.png)"
    )
    assert "<img" not in html and "insight.pycal.org/badge" not in html
    assert '<span class="foreign-image" title="An image of insight.pycal.org, which ' in html
    assert ">Replies of Mrbozz</span></a>" in html
    assert ">Image of other.example</span>" in html


def test_the_images_of_the_site_stay(settings):
    settings.SITE_URL = "https://dashboard.example.org"
    html = render("![a & b](https://dashboard.example.org/p/badge.svg)")
    assert '<img src="/p/badge.svg" alt="a &amp; b">' in html and "foreign-image" not in html


def test_the_emoji_of_github_show_except_in_code():
    html = render(":x: no, :heavy_check_mark: yes, :unknown: `:x:`\n\n    :warning:")
    assert html.startswith("<p>❌ no, ✔️ yes, :unknown: <code>:x:</code></p>")
    assert "<pre><code>:warning:" in html
