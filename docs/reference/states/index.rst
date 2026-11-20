======
States
======

A state is observed on a pull request or on its author, like a condition: it
has an id, the inputs that configure it, and the data that the update of the
repository reads for it in the background. A condition
(:doc:`/reference/conditions/index`) is a state of a pull request that is true
or false; the states of people are numbers, counted in all repositories of a
project, such as the reviews a person gave. Conditions check them, such as
:doc:`/reference/conditions/review_ratio_above`.

.. list-table::
   :header-rows: 1

   * - Id
     - What it observes
   * - :doc:`pull_requests_opened`
     - How many pull requests a person opened in the project.
   * - :doc:`own_pull_requests_closed`
     - How many pull requests a person opened and closed themselves in the
       project.
   * - :doc:`reviews_given`
     - How many reviews a person gave in the project, without those of comments
       only.
   * - :doc:`review_ratio`
     - The reviews a person gave in the project for each pull request they
       opened and did not close themselves.

Where they count
================

The repositories counted are those of the project that the viewer sees
(:class:`~pycal_dashboard.conditions.state.scope.Scope`); the numbers of all
people are counted at once, with one query of the database each.

.. automodule:: pycal_dashboard.conditions.state.person
   :members:
   :show-inheritance:

.. automodule:: pycal_dashboard.conditions.state.scope
   :members:

.. toctree::
   :hidden:

   pull_requests_opened
   own_pull_requests_closed
   reviews_given
   review_ratio
