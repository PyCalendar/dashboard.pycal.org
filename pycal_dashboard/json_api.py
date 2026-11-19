"""The JSON of the public pages, for other sites and for agents: one list for all who show it.

``/llms.txt`` (the guideline for agents), ``/index.json`` and the reference of the
documentation list these pages; ``tests/test_agents.py`` checks that every page with JSON
(:data:`~pycal_dashboard.public_json.JSON_PAGES`) is here and answers.
"""

# the name of the page in urls.py, its address, its JSON, and what the JSON holds
JSON_API = [
    {
        "name": "home",
        "page": "/",
        "json": "/index.json",
        "holds": "the site, its version, whether people can sign in, its organizations, the "
        "documentation and the addresses of the other JSON (pages)",
    },
    {
        "name": "projects",
        "page": "/projects/",
        "json": "/projects.json",
        "holds": "the public projects, each with its name, slug, description, url and public "
        "repositories: start here",
    },
    {
        "name": "project",
        "page": "/projects/<slug>/",
        "json": "/projects/<slug>.json",
        "holds": "a public project with its open issues and pull requests, when it was "
        "updated, and its repositories with their numbers",
    },
    {
        "name": "project_pull_requests",
        "page": "/projects/<slug>/pull-requests/",
        "json": "/projects/<slug>/pull-requests.json?state=all&page=1",
        "holds": "the pull requests of all repositories of a project, the newest first, 50 a "
        "page: state is all, open, merged or closed; count, page and pages say how many",
    },
    {
        "name": "about",
        "page": "/about/",
        "json": "/about.json",
        "holds": "the version that runs, and the permissions and events of the GitHub App",
    },
    {
        "name": "licenses",
        "page": "/licenses/",
        "json": "/licenses.json",
        "holds": "the license of the site, the code it reuses and the Python packages it runs",
    },
]

# the pages that robots and agents leave alone: those of people, setup and the admin
PRIVATE = [
    "/account/",
    "/accounts/",
    "/admin/",
    "/logs/",
    "/setup/",
    "/github/",
    "/people/",
    "/repositories/",
    "/projects/new/",
    "/theme/",
    "/language/",
]
