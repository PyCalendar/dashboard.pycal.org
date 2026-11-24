=======================
The backup of a project
=======================

*Download the backup* on the tab *Settings → Backup* of a project saves a file of YAML with
all that the people of the project decided: the project, its repositories,
filters, steps with the skips of pull requests, message and roles; *Restore*
reads such a file back, see :ref:`project-backup`. Writers and owners of the
project download backups; only the owners restore them, because a backup can
replace filters and steps. The file starts with a comment that says what it is
and links this page. A snapshot keeps the same file on dashboard.pycal.org, see
:ref:`snapshots`; downloaded, it restores as a backup.

.. code-block:: yaml

   # A backup of the project iCalendar of https://dashboard.pycal.org.
   # The format, version 1: https://docs.dashboard.pycal.org/reference/backup.html
   dashboard_backup: 1
   documentation: https://docs.dashboard.pycal.org/reference/backup.html
   exported: '2026-11-20T09:00:00+00:00'
   site: https://dashboard.pycal.org
   project:
     name: iCalendar
     slug: icalendar
     description: The calendar library of Python.
     public: true
     step_labels: sync
   repositories:
   - collective/icalendar
   filters:
   - name: Review
     description: Waiting for a review.
     columns:
     - labels~applies~present~needs review
     - status~all~open
   steps:
   - name: Review
     filter: Review
     summary: Thanks, {author_mention}!
     hidden: false
     color: '#bfdbfe'
     tasks:
       labels~applies~present~needs review:
         summary: Review it
         description: Ask in the chat.
     actions:
       enter:
         add: [needs review]
         remove: []
       complete:
         add: []
         remove: [needs review]
     skip_authors: [niccokunzmann]
     skips:
     - repository: collective/icalendar
       number: 2185
       by: niccokunzmann
       reason: Reviewed in the chat.
       created: '2026-11-19T10:00:00+00:00'
   message:
     template: '{pr_badge} **{step_name}** {tasks_all}'
     draft: '{pr_badge} **{step_name}**'
     listed: ['2166']
     to_listed: true
     to_new: false
     to_open: true
     to_closed: false
   members:
   - handle: niccokunzmann
     role: owner

The keys
========

``dashboard_backup``
   The version of the format, a number: 1. A site restores only the versions
   it knows; a newer version comes with a new version of the site.
``documentation``
   The address of this page.
``exported``, ``site``
   When and where the backup was made; restoring does not read them.
``project``
   ``name`` and ``description`` (Markdown), ``step_labels`` (``off`` or
   ``sync``, see :ref:`pr-message`), and ``slug`` and ``public``, which
   restoring leaves as they are: the address and the visibility of the project.
``repositories``
   The names of the repositories, such as ``collective/icalendar``. Restoring
   adds those that the project lacks, as the tab *Repositories* does, with the
   rights of the person who restores: a private repository needs the GitHub
   App, and goes only into a private project.
``filters``
   The saved filters, each with its ``name``, unique in the file, its
   ``description`` and its ``columns``: the columns of conditions as the
   address of the table keeps them, see :ref:`condition-columns`.
``steps``
   The steps from left to right, each with its ``name``, the name of its
   ``filter`` in the file, its ``summary``, whether it is ``hidden`` in the
   page of a pull request, its ``color`` (such as ``#bfdbfe``, or empty), the
   ``tasks`` (the ``summary`` and ``description`` of each condition of its
   filter, by the column) and its ``actions``: the labels to ``add`` and to
   ``remove`` when a pull request will ``enter`` the step or ``complete`` it, and
   ``skip_authors``, the GitHub handles of the authors whose pull requests skip
   it. Its ``skips`` are the pull requests that skip it because a person said
   so: the ``repository`` and ``number`` of the pull request, the GitHub handle
   of the person (``by``), the ``reason`` and when it was ``created``.
``message``
   The Status Message of the tab *PR Sync*, see :ref:`pr-message`: its
   ``template``, the edited message that is not applied yet (``draft``, empty
   when there is none), the pull requests ``listed`` by their numbers, and the
   switches of its scope, ``to_listed``, ``to_new``, ``to_open`` and
   ``to_closed``; empty without a message. New pull requests count from the time
   of restoring.
``members``
   The roles in the project: the GitHub ``handle`` of each person and the
   ``role``, ``read``, ``write`` or ``owner``.

The file is sorted inside, so that the same project always gives the same
file and two backups or snapshots compare line by line, such as with ``diff``:
the repositories, the filters and the members by their names, the skips by
the repository and the number of the pull request, and the GitHub handles,
the numbers of pull requests (``listed``), the labels of the ``actions`` and
the keys of the ``tasks``. Only ``exported`` differs between two backups of an
unchanged project. The steps keep their order from left to right, and the
``columns`` of a filter theirs, as the order of both means something. Restoring
does not count a different order of the rest as a change.

A backup keeps everything that the people of a project decide;
``tests/test_backup.py`` checks every field. Left out are the ids and times of
the database, who made or changed something last, and what GitHub tells, which
the next update reads again: the labels of the steps on GitHub, which step a
pull request is in, and the comments of PR Sync.

Restoring
=========

Restoring compares the file with the project first and shows what it changes;
nothing changes until **Restore the backup** on that page. Filters and steps
are the same when their names are.

- What only adds is restored: the filters and steps that the project lacks (new
  steps come last), the message when the project has none, the skips of pull
  requests that the project knows, and the repositories that it lacks, as the
  tab *Repositories* adds them.
- What deletes or replaces something happens only when it is ticked, and
  nothing is ticked at first: a filter or a step that differs from the backup is
  replaced, one added after the backup is deleted (a filter with its step), the
  name, the description, the step labels and the message are replaced, and the
  steps are ordered as in the backup. A role is given only when it is ticked,
  too; a person who never signed in gets none.

When steps change, restoring forgets which step each open pull request was in:
the next update only records it, so no label is added or removed because of the
restored steps. A file that is not a backup, has another version,
or has a wrong part, such as a step whose filter is not in the file, changes
nothing: the page says what is wrong, see
:class:`~pycal_dashboard.errors.projects.BackupInvalid` and
:class:`~pycal_dashboard.errors.projects.BackupVersionUnknown`.

.. automodule:: pycal_dashboard.services.project_backup
   :members:

.. automodule:: pycal_dashboard.services.restore_plan
   :members:

.. automodule:: pycal_dashboard.services.restore_change
   :members:
