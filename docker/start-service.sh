#!/bin/sh
# Prepare the database and say whether the GitHub App must be registered, then serve: nginx on $PORT in front of gunicorn on 127.0.0.1:8000.
set -e
# nginx first: while the database is prepared, it answers with docker/starting.html
sed "s/LISTEN_PORT/${PORT}/g" /app/docker/nginx.conf > /tmp/nginx.conf
nginx -c /tmp/nginx.conf
# migrates; without a GitHub App it prints where to register it, with the setup code
python manage.py prepare
# the installations of the GitHub App: a new version may need more permissions, which the
# people of each installation are told by email
(python manage.py check_installations || true) &
# the updates that wait, such as those that a migration of the data of GitHub queued, and every
# hour those of the repositories not read in the last day: a process that ends each time
(while true; do python manage.py update_projects --stale || true; sleep 3600; done) &
# a low footprint when idle: fewer arenas of malloc for the threads, and every worker is replaced
# after about 1000 requests, which returns the memory that a busy time made it grow by
export MALLOC_ARENA_MAX=2
# the background updates run in a thread of the worker: a longer timeout than gunicorn's 30
# seconds, so that a long update does not get the worker killed; nginx logs the requests
exec gunicorn pycal_dashboard.wsgi -w "$WORKERS" --threads "$THREADS" -b "127.0.0.1:8000" \
    --timeout "$TIMEOUT" --max-requests 1000 --max-requests-jitter 100
