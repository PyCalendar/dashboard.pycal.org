#!/bin/sh
# Prepare the database and say whether the GitHub App must be registered, then serve: nginx on $PORT in front of gunicorn on 127.0.0.1:8000.
set -e
# nginx first: while the database is prepared, it answers with docker/starting.html
sed "s/LISTEN_PORT/${PORT}/g" /app/docker/nginx.conf > /tmp/nginx.conf
nginx -c /tmp/nginx.conf
# migrates; without a GitHub App it prints where to register it, with the setup code
python manage.py prepare
# the background work (webhooks, updates and what follows them) as in community-insights: with
# FETCH_WORKER=external-http-container (the default of the image) a process of its own, started
# again when it stops, such as out of memory; external-separate-container runs it in the worker
# service of docker-compose.yml; internal in a thread of gunicorn, with the hourly renewal here
case "$FETCH_WORKER" in
  external-http-container)
    (while true; do python manage.py fetch_worker || true; sleep 5; done) & ;;
  internal)
    (python manage.py check_installations || true) &
    (while true; do python manage.py update_projects --stale || true; sleep 3600; done) & ;;
esac
# a low footprint when idle: fewer arenas of malloc for the threads, and every worker is replaced
# after about 1000 requests, which returns the memory that a busy time made it grow by
export MALLOC_ARENA_MAX=2
# the background updates run in a thread of the worker: a longer timeout than gunicorn's 30
# seconds, so that a long update does not get the worker killed; nginx logs the requests
exec gunicorn pycal_dashboard.wsgi -w "$WORKERS" --threads "$THREADS" -b "127.0.0.1:8000" \
    --timeout "$TIMEOUT" --max-requests 1000 --max-requests-jitter 100
