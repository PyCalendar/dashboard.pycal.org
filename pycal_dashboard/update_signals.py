"""The signals of the updates from GitHub: what changed, for the places that show it.

Every update takes the same path, whoever started it: the button *Update*, a webhook of GitHub,
the update of what is out of date (every hour, and when a page shows that it is), or the start
after a migration. They all queue a job (``UpdateQueue``), the worker runs it in the background
(``RepositoryUpdate``), and the signals tell of the result:

- :data:`repository_updated` after a repository was read from GitHub, with ``repository``;
- :data:`project_updated` after the time of the last update of a project changed, with
  ``project``.

Receivers connect in ``pycal_dashboard/receivers.py``, such as the one that keeps the time of the
last update of the projects.
"""

from django.dispatch import Signal

repository_updated = Signal()
project_updated = Signal()
