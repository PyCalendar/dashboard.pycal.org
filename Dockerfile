FROM python:3.13-slim

COPY LICENSE /LICENSE

EXPOSE 5000
ENV PORT=5000
ENV WORKERS=2
ENV THREADS=4
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=true

# nginx in front of gunicorn serves the static files (docker/nginx.conf)
RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

# The versions are locked in uv.lock.
COPY pyproject.toml uv.lock README.md ./
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_PYTHON_DOWNLOADS=never
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --no-dev --no-install-project --frozen

COPY manage.py ./
COPY pycal_dashboard pycal_dashboard
COPY static static
COPY LICENSES LICENSES
COPY REUSE.toml ./
COPY docker/start-service.sh docker/healthcheck.py ./
COPY docker/nginx.conf docker/starting.html docker/
# throwaway key: nothing secret is written into the image
RUN SECRET_KEY=build DATA_DIR=/tmp/build python manage.py collectstatic --noinput \
 && mkdir -p /app/data && chmod 777 /app/data

VOLUME /app/data
HEALTHCHECK --start-period=60s --start-interval=5s --interval=30s --timeout=10s --retries=3 \
    CMD python healthcheck.py
ENTRYPOINT ["/bin/sh", "start-service.sh"]
