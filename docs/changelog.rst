=========
Changelog
=========

.. towncrier release notes start

0.1.0 (unreleased)
------------------

New features
~~~~~~~~~~~~

- The frame of the dashboard of the PyCalendar community, with a JSON API. It
  keeps no data of GitHub yet; the numbers and the automation come later.
- The GitHub App is registered on the site at its first start and receives the
  webhooks of the repositories it is installed on. It only reads: the site
  writes nothing to GitHub, such as labels.
- People sign in with GitHub through a separate OAuth app, install the GitHub App
  from their account, and have an account page with preferences and email
  addresses. The administrators of the site reach the Django admin.
- The documentation is published at https://docs.dashboard.pycal.org/.
