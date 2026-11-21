=======================
The backup of a project
=======================

*Download the backup* in the settings of a project saves a file of YAML with
the project, its repositories, its filters and its steps; *Restore* reads such a
file back, see :ref:`project-backup`. Writers and owners of the project download
backups; only the owners restore them, because a backup replaces the filters and steps. The file starts with a comment that says what it is and links
this page.

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
   message:
     template: '{pr_badge} **{step_name}** {tasks_all}'
     listed: ['2166']
     to_listed: true
     to_new: false
     to_open: true
     to_closed: false

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
   ``name`` and ``description`` (Markdown), which restoring sets, and ``slug``
   and ``public``, which restoring leaves as they are: the address and the
   visibility of the project.
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
   ``remove`` when a pull request will ``enter`` the step or ``complete`` it.
``message``
   The message of the tab *PR Message*, see :ref:`pr-message`: its
   ``template``, the pull requests ``listed`` by their numbers, and the
   switches of its scope, ``to_listed``, ``to_new``, ``to_open`` and
   ``to_closed``; empty without a message. Restoring sets it, with new pull
   requests from the time of restoring, and leaves the message as it is for a
   file without one.

Restoring
=========

Restoring replaces all filters and steps of the project with those of the file,
and the message, and sets its name and description. It forgets which step each open pull request
was in: the next update only records it, so no label is added or removed
because of the restored steps. A file that is not a backup, has another version,
or has a wrong part, such as a step whose filter is not in the file, changes
nothing: the page says what is wrong, see
:class:`~pycal_dashboard.errors.projects.BackupInvalid` and
:class:`~pycal_dashboard.errors.projects.BackupVersionUnknown`.

.. automodule:: pycal_dashboard.services.project_backup
   :members:
