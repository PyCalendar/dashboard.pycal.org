# The image of `make messages` without gettext on the computer: gettext and the packages of
# uv.lock, built once and again only when uv.lock or pyproject.toml change (cached layers).
# The sources are mounted at /src when it runs (Makefile).
FROM python:3.13-slim
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends gettext >/dev/null \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv SECRET_KEY=messages DATA_DIR=/tmp/data
WORKDIR /deps
COPY pyproject.toml uv.lock ./
RUN uv sync -q --frozen --no-dev --no-install-project
WORKDIR /src
