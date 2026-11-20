"""The site keeps its memory low when idle: heavy packages are loaded only when they are needed.

The pages that people and the health check of the container open every day must not load the
packages that only speak with GitHub or read the licenses. AGENTS.md makes it a rule.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# loaded only when the site speaks with GitHub, reads the licenses itself or draws a badge
HEAVY = ["httpx", "jwt", "cryptography", "reuse", "piplicenses", "anybadge", "PIL", "yaml"]
PAGES = [
    "/health/",
    "/",
    "/about/",
    "/licenses/",
    "/accounts/login/",
    "/about.json",
    "/projects/",
    "/projects.json",
]

SERVE = """
import json, sys
from pathlib import Path
import django
django.setup()
from django.conf import settings
# the static files are not collected for the tests
settings.STORAGES = {**settings.STORAGES, "staticfiles": {
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
from django.core.management import call_command
call_command("migrate", verbosity=0)
from pycal_dashboard import licenses
licenses.DATA = Path(sys.argv[1])  # as in the image, which reads the licenses when it is built
from django.core.wsgi import get_wsgi_application
from django.test import Client
get_wsgi_application()
client = Client()
codes = {page: client.get(page).status_code for page in json.loads(sys.argv[2])}
heavy = [name for name in json.loads(sys.argv[3]) if name in sys.modules]
print(json.dumps({"codes": codes, "heavy": heavy}))
"""


def test_the_pages_load_no_heavy_packages(tmp_path):
    """A fresh process serves the pages of every day without loading the heavy packages."""
    from pycal_dashboard import licenses

    data = tmp_path / "licenses.json"
    licenses.write(data)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GITHUB_", "DJANGO_", "DATABASE_"))
    }
    environment.update(
        DJANGO_SETTINGS_MODULE="pycal_dashboard.settings",
        DATA_DIR=str(tmp_path / "data"),
        SECRET_KEY="test",
        ALLOWED_HOSTS="testserver",
        SITE_URL="http://testserver",
        DEBUG="false",
    )
    (tmp_path / "data").mkdir()
    result = subprocess.run(
        [sys.executable, "-c", SERVE, str(data), json.dumps(PAGES), json.dumps(HEAVY)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    served = json.loads(result.stdout.strip().splitlines()[-1])
    assert served["codes"] == dict.fromkeys(PAGES, 200)
    assert served["heavy"] == []


def test_the_container_keeps_few_processes():
    """One worker of nginx and of gunicorn by default, recycled after a busy time."""
    nginx = (ROOT / "docker/nginx.conf").read_text()
    assert "worker_processes 1;" in nginx
    assert "ENV WORKERS=1\n" in (ROOT / "Dockerfile").read_text()
    start = (ROOT / "docker/start-service.sh").read_text()
    assert "MALLOC_ARENA_MAX=2" in start and "--max-requests" in start
