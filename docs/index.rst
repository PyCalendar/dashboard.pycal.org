===================
dashboard.pycal.org
===================

`dashboard.pycal.org <https://dashboard.pycal.org>`_ is the dashboard of the
contributor community of `PyCalendar <https://github.com/PyCalendar>`_, the
Python Calendaring Ecosystem. It answers three questions:

- **Where can I help?** Issues for newcomers and issues that nobody answered yet.
- **What waits for me?** Pull requests that wait for a review, the longest
  waiting first, and those without activity for a long time.
- **Who makes it happen?** The people who contribute, and those who contribute
  for the first time.

Its GitHub App labels the pull requests, such as with their size, so that
reviewers find small changes and welcome first contributions.

- **Contributors** read :doc:`tutorial/use`, and :doc:`tutorial/account` to
  sign in.
- **People who run the site** start the container and register the GitHub
  App: :doc:`how-to/run-docker` and :doc:`how-to/github-app`.
- **Developers** read :doc:`how-to/develop` and :doc:`reference/api`.

Why the dashboard exists and what it shows publicly is in
:doc:`explanation/purpose`.

.. note::

   Most of this project is written with AI: Claude Code makes the changes
   from the prompts of a person, who reviews them. The prompts are recorded in
   the commit messages, as :doc:`contribute` explains.

.. toctree::
   :maxdepth: 2

   tutorial/index
   how-to/index
   reference/index
   explanation/index
   contribute
   changelog
