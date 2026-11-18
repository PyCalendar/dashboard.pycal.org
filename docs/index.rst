===================
dashboard.pycal.org
===================

`dashboard.pycal.org <https://dashboard.pycal.org>`_ is the dashboard of the
contributor community of `PyCalendar <https://github.com/PyCalendar>`_, the
Python Calendaring Ecosystem. It will answer three questions: where can I
help, what waits for me, and who makes it happen.

The numbers and the automation are designed next, as separate functionality.
Until then the site signs people in with GitHub and receives the webhooks of
its GitHub App, which people install on repositories. It keeps no data of
GitHub and writes nothing to GitHub, such as labels or comments.

- **Contributors** read :doc:`tutorial/use`, and :doc:`tutorial/account` to
  sign in.
- **People who run the site** start the container, register the GitHub App
  and the OAuth app, and install the app: :doc:`how-to/run-docker`,
  :doc:`how-to/github-app` and :doc:`how-to/install-app`.
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
