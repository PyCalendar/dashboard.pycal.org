==========
Contribute
==========

Contributions are welcome: open an issue or a pull request on `GitHub
<https://github.com/PyCalendar/dashboard.pycal.org>`_. :doc:`how-to/develop`
sets up the development environment.

People who use AI follow the `AI policy of icalendar and the Python Calendaring
Ecosystem <https://icalendar.readthedocs.io/en/latest/contribute/index.html>`_.
The prompts of AI agents are recorded with `ai-prompt-auto-commit
<https://github.com/PyCalendar/ai-prompt-auto-commit>`_ and added to the commit
messages; ``make dev`` installs its hooks. ``todo.txt`` lists the requirements
of the prompts and what is open.

Every change that people notice has a news fragment in ``news/``, such as
``news/12.feature.rst``, and updates the documentation.

.. _license:

License
=======

dashboard.pycal.org is free software under the `AGPL-3.0-or-later
<https://www.gnu.org/licenses/agpl-3.0.html>`_: you may use, study, share and
change it; a changed version that you run for others must offer its source
code. The project follows the `REUSE specification <https://reuse.software/>`_:
``REUSE.toml`` says the copyright and license of every file, the texts are in
``LICENSES/``. The icon of pycal is under CC-BY-SA-4.0, the mark of GitHub
under MIT. ``make reuse`` checks it.

The page ``/licenses/`` of the site lists these licenses and those of the
Python packages that run on the server.
