"""The page while the site starts: with JavaScript, it waits for /health/; never 405."""

from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_the_starting_page_asks_the_health_check():
    page = (ROOT / "docker" / "starting.html").read_text()
    assert '<script src="/static/starting.js" defer></script>' in page
    # the reload only without JavaScript: the script opens the page again with GET
    assert '<noscript><meta http-equiv="refresh" content="10"></noscript>' in page
    script = (ROOT / "static" / "starting.js").read_text()
    assert 'fetch("/health/"' in script and "location.replace" in script
    assert "answer.status === 405" in script  # a page that only takes a form: back
    assert "location.reload" not in script  # a reload would send a form again


def test_nginx_serves_the_static_files_while_the_site_starts():
    conf = (ROOT / "docker" / "nginx.conf").read_text()
    assert "location /static/" in conf and "alias /app/staticfiles/;" in conf
