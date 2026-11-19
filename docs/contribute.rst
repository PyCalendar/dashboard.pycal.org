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
``news/12.feature`` or ``news/+topic.bugfix``, and updates the documentation.
Each build of the documentation drafts the fragments with towncrier into the
section *Unreleased* of :doc:`changelog`; ``towncrier build`` writes them into
the changelog at a release.

.. _translate:

Translate
=========

The site speaks English, German and Spanish. The language comes from the
browser; the menu with the globe at the top keeps another choice in a cookie.
The texts are in ``pycal_dashboard/locale/<language>/LC_MESSAGES/django.po``.

Improve a translation
---------------------

#. Change the ``msgstr`` of the text in :file:`django.po`.
#. Run ``make messages``: it updates the texts of all languages and compiles
   them into :file:`django.mo`. It uses gettext, or Docker if gettext is not
   installed.
#. ``make test`` checks that every text of German and Spanish is translated,
   that none is marked ``fuzzy`` and that :file:`django.mo` is compiled.

A changed English text makes ``make messages`` mark its translation
``#, fuzzy`` or add an empty ``msgstr``: translate it and remove the mark.

Add a language
--------------

#. Add it to ``LANGUAGES`` in ``pycal_dashboard/settings.py`` and to
   ``MESSAGES`` in the ``Makefile``, such as ``-l fr``.
#. Run ``make messages`` and translate
   :file:`pycal_dashboard/locale/fr/LC_MESSAGES/django.po`.

Texts in the templates are in ``{% translate %}`` or ``{% blocktranslate %}``;
texts in Python in ``gettext``. A text without them stays English, and a test
finds it. The JSON of the pages, the log and the details of errors to copy stay
English.

.. _lazy-imports:

Lazy imports
============

The site imports the packages that it needs only now and then inside the
functions that use them, which keeps its memory low, see :ref:`memory`. Each
such import goes through the import guard, so that threads that serve pages at
the same time cannot stop each other in a deadlock:

.. code-block:: python

   from pycal_dashboard.import_guard import IMPORT_GUARD

   def token():
       with IMPORT_GUARD:  # see import_guard.py
           import jwt
       ...

``tests/quality/test_lazy_imports.py`` checks that every import inside a
function is inside ``with IMPORT_GUARD:``.

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
