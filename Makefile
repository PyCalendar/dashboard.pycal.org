.DEFAULT_GOAL = help
SHELL         = bash
PYTHONVERSION = >=3.13,<3.15
PORT         ?= 5000
DOCS_PORT    ?= 8000
# the tests run on all processors (pytest-xdist); JOBS=0 runs them in one process
JOBS         ?= auto
IMAGE        ?= dashboard-pycal
# the settings of .env are used by make run, if it exists
ENV_FILE      = $(if $(wildcard .env),--env-file .env)
# make run: a local site that needs no setup code to register its GitHub App
RUN_ENV       = DEBUG=true SITE_URL=$${SITE_URL:-http://localhost:$(PORT)}

.PHONY: help
help:  ## This help message
	@grep -E '^[a-zA-Z_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: dev
dev:  ## Set up the development environment: Python, packages, git hooks, prompt recording, database
	@uv python install "$(PYTHONVERSION)"
	@uv sync --python "$(PYTHONVERSION)" --group dev --group browser --extra docs
	@uv run pre-commit install
	@uv run pre-commit run --hook-stage manual prepare-ai-repository || true
	@uv run $(ENV_FILE) python manage.py migrate
	@echo "Ready. Start the site with: make run"

.venv:
	@$(MAKE) --no-print-directory dev

.PHONY: migrate
migrate: .venv  ## Create or update the database
	@uv run $(ENV_FILE) python manage.py migrate

.PHONY: migrations
migrations: .venv  ## Create the migrations of changed models
	@uv run python manage.py makemigrations pycal_dashboard

.PHONY: run
run: .venv  ## Run the site on http://localhost:$(PORT) with the settings of .env
	@$(RUN_ENV) uv run $(ENV_FILE) python manage.py prepare
	@$(RUN_ENV) uv run $(ENV_FILE) python manage.py runserver "$(PORT)"

.PHONY: sync
sync: .venv  ## Read the repositories, issues and pull requests of the installations from GitHub
	@uv run $(ENV_FILE) python manage.py sync_repositories

.PHONY: app-manifest
app-manifest: .venv  ## Print the manifest of the GitHub App
	@uv run $(ENV_FILE) python manage.py app_manifest

MESSAGES = makemessages -l de -l es --no-obsolete --no-location --ignore=.venv --ignore=docs \
	--ignore=tests --ignore=build --ignore=scripts --ignore=data --ignore=staticfiles

.PHONY: messages
messages: .venv  ## Update the texts to translate in pycal_dashboard/locale and compile them (gettext, else Docker)
	@if command -v xgettext >/dev/null; then \
	  uv run python manage.py $(MESSAGES) && uv run python manage.py compilemessages --ignore=.venv; \
	else \
	  docker run --rm -v "$(CURDIR):/src" -w /src -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
	    -e SECRET_KEY=messages -e DATA_DIR=/tmp/data python:3.13-slim sh -c '\
	    apt-get update -qq && apt-get install -y -qq --no-install-recommends gettext >/dev/null \
	    && pip install -q uv && uv sync -q --frozen --no-dev \
	    && uv run --no-sync python manage.py $(MESSAGES) \
	    && uv run --no-sync python manage.py compilemessages --ignore=.venv \
	    && chown -R $(shell id -u):$(shell id -g) pycal_dashboard/locale'; \
	fi

.PHONY: test
test: .venv  ## Run the unit and API tests on all processors with coverage; check the migrations
	@uv run python manage.py makemigrations --check --dry-run
	@uv run pytest -n "$(JOBS)" --cov=pycal_dashboard --cov-branch --cov-report=term --cov-report=xml

.PHONY: browser-test
browser-test: .venv  ## Run the browser tests in Chromium (Playwright), on all processors
	@uv run --group browser pytest -o addopts= -n "$(JOBS)" -p no:cacheprovider tests/browser

.PHONY: browser-install
browser-install: .venv  ## Install Chromium for the browser tests
	@uv run --group browser playwright install --only-shell chromium

.PHONY: lint
lint: .venv  ## Check the code style
	@uv run ruff check .
	@uv run ruff format --check .

.PHONY: format
format: .venv  ## Format the code
	@uv run ruff check --fix .
	@uv run ruff format .

.PHONY: docs
docs:  ## Build the documentation; warnings fail
	@uv run --extra docs sphinx-build -W -n --keep-going -b html docs docs/_build/html

.PHONY: livehtml
livehtml:  ## Show the documentation on http://localhost:$(DOCS_PORT) while editing it
	@uv run --extra docs sphinx-autobuild --port "$(DOCS_PORT)" docs docs/_build/html

.PHONY: linkcheck
linkcheck:  ## Check the links of the documentation (needs the internet)
	@uv run --extra docs sphinx-build -b linkcheck docs docs/_build/linkcheck

.PHONY: changelog
changelog:  ## Check that there is a news fragment
	@uv run --extra docs towncrier check --compare-with origin/main

.PHONY: prose
prose:  ## Check the prose of the documentation with Vale (.vale.ini)
	@uv run --extra docs --with vale==3.26.0.1 vale docs/*.rst docs/*/*.rst docs/*/*/*.rst README.md

.PHONY: check-live
check-live: .venv  ## Check a live site as a visitor: LIVE_URL (default https://dashboard.pycal.org), waits while it starts
	@uv run python scripts/check_live.py

.PHONY: measure-speed
measure-speed: .venv  ## Measure the speed of every condition on a live site: LIVE_URL, PROJECT, LABEL
	@uv run python scripts/measure_speed.py --url "$${LIVE_URL:-https://dashboard.pycal.org}" --project "$${PROJECT:-icalendar}" --label "$${LABEL:-needs review}"

.PHONY: workflows
workflows:  ## Check the GitHub workflows for security problems with zizmor
	@uvx zizmor==1.32.0 --offline .github/workflows

.PHONY: reuse
reuse:  ## Check the licensing (REUSE)
	@uvx --quiet reuse lint

.PHONY: version
version:  ## Write the build information (commit, message, time, CI run) into pycal_dashboard/version.json
	@python3 docker/set_version.py

.PHONY: docker-build
docker-build: version  ## Build the container
	docker build -t $(IMAGE) .

.PHONY: docker-test
docker-test: docker-build  ## Run the container and check that Docker sees it healthy
	@docker rm -f $(IMAGE)-test >/dev/null 2>&1 || true
	@docker run -d --name $(IMAGE)-test -e ALLOWED_HOSTS=dashboard.example.org $(IMAGE) >/dev/null
	@for i in $$(seq 60); do [ "$$(docker inspect -f '{{.State.Health.Status}}' $(IMAGE)-test)" = healthy ] && break; sleep 1; done; \
	status=$$(docker inspect -f '{{.State.Health.Status}}' $(IMAGE)-test); echo $$status; \
	[ "$$status" = healthy ] || docker logs $(IMAGE)-test; \
	docker logs $(IMAGE)-test 2>&1 | grep -q "setup code" || { echo "no setup code in the log"; status=no-code; }; \
	docker rm -f $(IMAGE)-test >/dev/null; [ "$$status" = healthy ]

TRIVY = aquasec/trivy:0.58.1
.PHONY: docker-scan
docker-scan: docker-build  ## Scan the image with Trivy: fails on critical vulnerabilities that have a fix
	@# the image is saved to a file, so Trivy needs no access to the socket of Docker
	@mkdir -p build && docker save $(IMAGE) -o build/$(IMAGE)-image.tar
	@docker run --rm -v "$(CURDIR)/build:/scan:ro" $(TRIVY) image --input /scan/$(IMAGE)-image.tar \
		--exit-code 1 --severity CRITICAL --ignore-unfixed --no-progress; \
		status=$$?; rm -f build/$(IMAGE)-image.tar; exit $$status

.PHONY: docker-run
docker-run: docker-build  ## Run the container on $(PORT) with ./data
	@mkdir -p data
	docker run --rm -p "$(PORT):5000" -v "$(CURDIR)/data:/app/data" --user "$$(id -u):$$(id -g)" \
		$(if $(wildcard .env),--env-file .env) $(IMAGE)
