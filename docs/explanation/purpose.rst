=======================
Purpose and privacy
=======================

Why a dashboard
===============

PyCalendar has many repositories: icalendar, the calendar tools and their
documentation. GitHub shows each repository alone. A newcomer does not know
where to start, and maintainers do not see which pull request waited longest.
The dashboard puts the organization on one page and guides the community:

- newcomers find issues that are meant for them,
- reviewers find the pull requests that wait, small ones first,
- first contributions are welcomed and labeled,
- everybody sees who contributes, which says thank you.

`community-insights <https://community-insights.readthedocs.io/>`_ measures
response times in depth; the dashboard is the daily start page. It looks like
`sign.pycal.org <https://sign.pycal.org>`_, the site where contributors sign
the AI policy.

What is public
==============

Every page is public, except pages based on private information:

- the page *Account* with the preferences and the email addresses, only for
  the person,
- the webhook deliveries, only for the administrators, because they may name
  private repositories.

Private repositories are stored when the app reads an installation, but never
shown, not even their numbers. Contributor pages show what GitHub already shows
publicly. The API returns the same public data.

Signing in
==========

People sign in with GitHub only; the dashboard has no passwords. GitHub tells
it who they are and their email addresses. It stores no token of theirs and
never writes to GitHub on their behalf. Only the GitHub App writes: the labels
of pull requests.
