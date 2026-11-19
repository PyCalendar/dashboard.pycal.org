"""The version of what the site keeps of GitHub.

Raise :data:`DATA_VERSION` with every change of what the site reads of a repository, such as a
new field of :class:`~pycal_dashboard.models.Issue`, together with its migration. A repository
read with an older version, or never read completely, is read completely again: ``manage.py
prepare`` queues the updates of its projects at the start after the migration, and
``manage.py update_projects`` runs them in the background.
"""

# 1: the issues and pull requests, open and closed, with title, author, times and description
# 2: the labels of the repositories and of the issues; the state of open pull requests
DATA_VERSION = 2
