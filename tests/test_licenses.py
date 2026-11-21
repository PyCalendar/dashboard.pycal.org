"""The page of the licenses: the project, code from other projects, the Python packages."""

import json
from pathlib import Path

import pytest

from pycal_dashboard import licenses

pytestmark = pytest.mark.django_db


def test_the_about_page_links_the_licenses_not_the_footer(client):
    footer = client.get("/").content.decode().split('<footer class="footer">')[1]
    assert 'href="/licenses/"' not in footer and "AGPL" not in footer
    about = client.get("/about/").content.decode().split("<main")[1].split("</main>")[0]
    assert 'href="/licenses/"' in about  # the tab Licenses
    version = client.get("/about/version/").content.decode()
    assert "AGPL-3.0-or-later" not in version and "data-all-licenses" not in version


def test_the_page_lists_the_licenses(client):
    page = client.get("/licenses/").content.decode()
    for name in ("AGPL-3.0-or-later", "CC-BY-SA-4.0", "MIT"):
        assert f'href="/licenses/{name}/"' in page
    reused = page.split('id="reused"')[1].split("</section>")[0]
    assert "<code>pycal_dashboard/github_mark.py</code>" in reused and "GitHub Inc." in reused
    assert "<code>static/img/favicon.png</code>" in reused
    packages = page.split('id="packages"')[1]
    assert ">Django</a>" in packages and ">reuse</a>" in packages


def test_license_texts(client):
    response = client.get("/licenses/AGPL-3.0-or-later/")
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert b"GNU AFFERO GENERAL PUBLIC LICENSE" in response.content
    assert client.get("/licenses/NOPE/").status_code == 404
    assert client.get("/licenses/../settings/").status_code == 404


def test_package_license_texts(client):
    assert b"Django Software Foundation" in client.get("/licenses/packages/django/").content
    assert client.get("/licenses/packages/not-installed/").status_code == 404


def test_the_image_contains_the_license_texts():
    dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text()
    assert "COPY LICENSES LICENSES" in dockerfile and "COPY REUSE.toml" in dockerfile


def test_the_image_reads_the_licenses_when_it_is_built():
    dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text()
    assert "python -m pycal_dashboard.licenses" in dockerfile


def test_the_site_reads_the_licenses_from_the_file(tmp_path, monkeypatch, client):
    """With licenses.json, as in the image, the page shows what the file says."""
    path = tmp_path / "licenses.json"
    licenses.write(path)
    data = json.loads(path.read_text())
    assert "django" in data["installed"] and "licensetext" in data["installed"]["django"]
    data["installed"]["django"]["version"] = "9.9.9-from-the-file"
    path.write_text(json.dumps(data))
    monkeypatch.setattr(licenses, "DATA", path)
    licenses.packages.cache_clear()
    try:
        assert b"9.9.9-from-the-file" in client.get("/licenses/").content
        assert b"Django Software Foundation" in client.get("/licenses/packages/django/").content
        assert licenses.reused() == licenses.read_reused()
    finally:
        licenses.packages.cache_clear()
