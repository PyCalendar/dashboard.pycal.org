=========================
Labels of pull requests
=========================

The GitHub App labels open pull requests when they are opened, reopened,
pushed to, edited or marked ready for review, and when the repositories are
read again (``manage.py sync_repositories``). ``PULL_REQUEST_LABELS`` chooses
the rules, separated by commas; the default is ``size,first-contribution``.

Each rule owns its labels. It adds the label that applies and removes its other
labels, with the smallest change. Labels of people are never touched. The page
*Labels* of the site lists the latest changes and their rules.

``size``
========

The lines a pull request adds and removes:

=============  ==================
Label          Changed lines
=============  ==================
``size: XS``   up to 9
``size: S``    up to 49
``size: M``    up to 249
``size: L``    up to 999
``size: XL``   1000 or more
=============  ==================

Reviewers find small pull requests quickly; large ones may be split.

``first-contribution``
======================

``first contribution``: GitHub says that the author has not contributed to the
repository before. Maintainers welcome them and guide them through their first
review.

The labels are created in the repository with the colors of the dashboard if
they do not exist.
