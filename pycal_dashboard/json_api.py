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
        "json": "/projects/<slug>/pull-requests.json?per_page=100&page=1",
        "holds": "the pull requests of all repositories of a project, the newest first: "
        "per_page is 10, 25, 50 or 100 (at most); count, page and pages say how many",
    },
    {
        "name": "project_filters",
        "page": "/projects/<slug>/filters/",
        "json": "/projects/<slug>/filters.json",
        "holds": "the saved filters of a project: name, description, columns of conditions, "
        "how many pull requests each shows, and the address of its pull requests",
    },
    {
        "name": "project_pull_request",
        "page": "/projects/<slug>/pull/<number>/",
        "json": "/projects/<slug>/pull/<number>.json",
        "holds": "a pull request of a project with the steps it goes through: the step it is "
        "in, and each step with its tasks, whether each is todo, done or unknown; repository "
        "chooses when several repositories have a pull request of the number",
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

# the addresses that only show the same pages again in other ways: robots leave them alone,
# so that a crawler does not read every pull request with every step and every column
REPEATED = [
    "/*?step=",
    "/*&step=",
    "/*?col=",
    "/*&col=",
    "/*?example=",
    "/*?pull=",
    "/*?view=",
    "/*?tab=",
    "/*/badge.svg",
    "/*/badge.png",
    "/projects/*/message/review/",
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
    "/markdown/",
    "/theme/",
    "/language/",
]
