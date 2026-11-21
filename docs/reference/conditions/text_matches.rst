==============================
``text_matches``: Text matches
==============================

The title or the description of a pull request matches a text or a regex.

Holds when the text of the input ``field`` matches the input ``text`` as the
input ``mode`` says. The case of letters does not matter, unless
``case_sensitive`` is on. The column *Text* has it.

A regex is a regular expression of Python, such as ``^(fix|feat):``, of at most
100 characters. Repetitions of groups that repeat themselves, such as
``(a+)+``, and back-references, such as ``\1``, are refused: they can take very
long to match, and the table of pull requests evaluates the columns of its
address for every visitor.

It is checked on pull requests only. While the data of a pull request is not
complete, the condition cannot be assessed yet.

Inputs
======

.. list-table::
   :header-rows: 1

   * - Name
     - Type
     - Required
     - What it is
   * - ``field``
     - ``choice``
     - yes
     - ``title`` or ``description``.
   * - ``mode``
     - ``choice``
     - yes
     - ``starts`` (starts with), ``ends`` (ends with), ``contains`` or
       ``regex``.
   * - ``text``
     - ``string``
     - yes
     - The text to match, or the regex, at most 100 characters.
   * - ``case_sensitive``
     - ``bool``
     - no, ``false``
     - Whether the case of letters matters.

The inputs as JSON:

.. code-block:: json

   {"field": "title", "mode": "regex", "text": "^(fix|feat):"}

In the address of the table, such as ``text~applies~title~starts~fix``; a column
that matches the case ends with ``~case``.

Data
====

The update of the repository reads in the background:

``issue``
   Whether the pull request is open, closed or merged, its title and its
   description. Permissions of the GitHub App: ``pull_requests``: read;
   webhooks: ``pull_request``.

API reference
=============

.. autoclass:: pycal_dashboard.conditions.condition.text_matches.TextMatches
   :members: assess
   :show-inheritance:
