=======================
Purpose and privacy
=======================

Why a dashboard
===============

PyCalendar has many repositories: icalendar, the calendar tools and their
documentation. GitHub shows each repository alone. A newcomer does not know
where to start, and maintainers do not see which pull request waited longest.
The dashboard will put the organization on one page and guide the community:

- newcomers find issues that are meant for them,
- reviewers find the pull requests that wait, small ones first,
- first contributions are seen and welcomed,
- everybody sees who contributes, which says thank you.

Step by step
============

The numbers and the automation are separate functionality, designed later.
For now the site is the frame: it signs people in, receives the webhooks of its
GitHub App and logs them. Of GitHub, it keeps only the installations of its
app with their permissions, to tell people when an installation needs more, and
it writes nothing to GitHub.

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

Private repositories are never shown. Of GitHub, the site keeps only the
installations of its app: the account, the permissions and events, and the
people who installed or changed it, who see it on their page *Account*. The
log of the webhooks keeps only the event, the action and the name of the
repository, for the administrators.

Signing in
==========

People sign in with GitHub only, through an OAuth app; the dashboard has no
passwords. GitHub tells it who they are and their email addresses. It stores no
token of theirs and never writes to GitHub on their behalf. The GitHub App only
reads, too: the dashboard adds no labels and writes no comments.
