========
Projects
========

A project is a set of repositories on GitHub that people look at together,
such as the repositories of the Python Calendaring Ecosystem. Its page shows
how many issues and pull requests are open.

The page *Projects*, in the menu at the top, lists every public project, and
the private projects you have a role in.

Create a project
================

Sign in with GitHub, open *Projects* and press **+ Create a project**. Enter:

- the **name**, such as *icalendar*,
- the **description**: what the project is about, in Markdown. The bar above
  the field makes text bold or italic, adds links, lists, quotes and code;
  **Preview** shows it as the page will. Without JavaScript, you type the
  Markdown yourself, such as ``**bold**`` and ``[a link](https://pycal.org)``.
  Images show only from dashboard.pycal.org, such as the badges of pull
  requests, and from the hosts that the administrators allow, see
  :ref:`site-settings`: it loads nothing else from other sites. An image of
  another site shows its text in a dashed frame instead; pull requests on
  GitHub show the image itself.
  Lists of tasks, ``- [ ]`` and ``- [x]``, show checkboxes as on GitHub, which
  show the state but cannot be changed. The emoji of GitHub that the messages
  use, ``:x:``, ``:heavy_check_mark:``, ``:grey_question:``,
  ``:white_check_mark:`` and ``:warning:``, show as on GitHub.
- the **visibility**: *Public*, the default, for everybody, or *Private*, only
  for its collaborators, see :ref:`project-roles`,
- optionally its **address**, see :ref:`project-address`.

You own the project you create. Next, the site asks for its repositories.

.. _project-address:

The address
===========

A project is at ``/projects/<address>/``, such as ``/projects/icalendar/``,
and its pages below it, such as ``/projects/icalendar/settings/``. Links of
before, with the name of the project after the address, lead there.

- Without a chosen address, a project gets a random one of six hexadecimal
  digits, such as ``3f9a0c``; also a project made in the Django admin.
- An address has the letters of a GitHub handle: ``a`` to ``z``, ``0`` to
  ``9`` and single hyphens inside, and at most one ``~`` between an account and
  a repository, such as ``collective~icalendar``. Capital letters become small
  ones. ``new`` belongs to the site.
- When the project has one repository, the site suggests an address after it:
  the name of the repository, such as ``icalendar``; if another project has it,
  ``collective~icalendar``; then ``collective~icalendar-2``, ``-3`` and so on.
  Press *Use it* on the tab *Settings → Repositories* or *Settings → Display*.
- The owners change the address on the tab *Settings → Display*. Old links keep working:
  the old address leads to the new one. Every address a project had is kept
  with the time it was used, listed under *Old addresses*, and no other project
  ever gets it, also after the project was deleted. A project may go back to an
  old address of its own.

.. _add-repositories:

Add repositories
================

On the tab *Settings → Repositories* of the project, add repositories in one of three
ways:

By name
   Type ``owner/name``, such as ``collective/icalendar``, or paste a link to
   the repository. While you type, the field proposes the repositories that the
   site knows and those of all of GitHub. Without JavaScript, it proposes those
   the site knows.
From an account
   Choose yourself or one of your organizations and press *Show its
   repositories*, then tick the repositories and press *Add the chosen
   repositories*.
Search
   Search all of GitHub by name and tick the repositories you want.

A repository can be in several projects. To list your organizations, the site
reads them with the token that GitHub gave it when you signed in (the scope
``read:org``, read only). If the site has no token of yours, it says so: sign
out and sign in again.

.. _private-repositories:

Private repositories
====================

A private repository can be added only

- to a private project, and
- if the GitHub App is installed on it, and
- if you may read it on GitHub.

The site finds it through its GitHub App: type its name. It never asks your
GitHub account for access to private repositories. A project with private
repositories cannot be made public. Only the collaborators of the project see them;
if a repository of a public project becomes private, the visitors no longer
see it.

Install the GitHub App
======================

After adding repositories, the tab *Settings → Repositories* says on which of them the
GitHub App is installed. The section *Install the GitHub App* shows up only
while a repository lacks the app or the permissions it needs now. Installed,
the app lets the site

- receive the webhooks of the changes in the repositories,
- add and remove labels of pull requests,
- create and update a comment of the site on a pull request.

:doc:`/reference/permissions` lists the permissions it asks for and why. An
owner of the account of a repository installs it with **Install the GitHub
App**, see :doc:`/how-to/install-app`.

When a new version of the site needs more permissions, the writers and owners
of the projects with a repository of the installation get an email with the
link to the page on GitHub where the permissions are accepted, see
:ref:`new-permissions`.

.. _project-update:

The overview and the update
===========================

The overview of a project shows the number of open issues and open pull
requests of all its repositories and of each one. At the bottom, it says
whether the project is up to date and when it was last updated, in your time
zone.

When repositories are added, the site updates them from GitHub in the
background at once. **Update** updates them again. A progress bar shows how many
are updated, with a turning circle; the box *Updating* reads itself again every 10
seconds, not the whole page, and shows a check mark with the new numbers when the
update ends. Without JavaScript, the page reloads itself instead. The project is *up
to date* when every repository was updated in the last day without an error. A
repository that could not be updated shows why: a notice at the top of the
overview names each one with its error, linked to the documentation of the
error. Its *Details to copy* hold what helps to find the cause, such as the
request, the answer of GitHub and its request id, the time and the version of
the site, but no tokens or data of people; paste them into a bug report or a
question. The cross clicks the notice away until a new failure comes.

The site reads a repository with the token of the GitHub App when the app is
installed on it, else without a token, which works for public repositories.
An update reads all issues and pull requests, open and closed: their title,
description, times, and who created them. The first update reads them all;
the next ones read only those that changed.

With the GitHub App installed, activity on GitHub, such as a new pull request
or a comment, updates its repository in the background: the webhook of GitHub
tells the site. Every hour, the site also updates the repositories that were
not read in the last day, which renews what no webhook tells of; and the
overview of a project that may be out of date starts its update when someone
opens it. A project is as fresh as its oldest repository.

.. _project-pull-requests:

Pull requests
=============

The tab *Pull requests*, public like the project, lists the pull requests of
all its repositories together, the newest first: 10, 25, 50 or 100 a page,
as the menu at its top right chooses. The tile with the number of open pull
requests on the overview leads there.

*Display* chooses the columns: the status, the title, the organization, the
repository, the number, the creator with their avatar, and when it was
created. First it shows the title, the number and the creator; the browser
keeps the choice. The title and the number link the pull request on GitHub;
without both, an icon of GitHub links it. Without the status, each row starts
with the color of its status: green while it is open, purple when it was
merged, red when it was closed without merging.

.. _condition-columns:

Columns of conditions
---------------------

The button **+** at the right of the table adds a column of conditions; each
says for every pull request whether its condition applies, with a green
check mark, or not, with a red cross, and why:

**Label**
   A label is present or absent. Choose a label of the repositories or type
   another one; the cell shows the label in its color.
**Branch**
   Up to date, outdated or in conflict with its base branch, as many as you
   switch on; a merged pull request is up to date. The cell names what applies.
**CI**
   Passing, failing or unknown: the last complete result of the checks, also
   while new ones run. The checks are read for open pull requests only, so the
   CI of closed and merged ones is unknown, as is that of open ones whose checks
   are not read yet or that the GitHub App may not read; the menu says so.
**Status**
   Open, closed, merged, auto-merging or *draft*, not ready for review yet, with
   their colors. A draft is open, too; see :doc:`/reference/conditions/draft`.
**Reviews**
   The pull request has a number of reviews: *at least* (the default), *at
   most*, *more than*, *fewer than* or *exactly*. At least and at most include
   the number. *Which reviews count*: approved, changes requested, commented
   and dismissed, all of them by default; a dismissed review is an approval or a
   request for changes that a maintainer dismissed later. By default, a review
   counts only when its author is not the author of the pull request; the
   switch *by the author of the pull request* counts those, too. The cell shows
   how many it has.
**Author**
   A state of the author compared with a number, counted in all repositories
   of the project that you see: the review to pull request ratio, the reviews
   given, the pull requests opened, or those of them closed by the author;
   *below* (the default), *above*, *at most*, *at least* or *exactly* the
   number. The ratio is the reviews given for each pull request that the
   author opened and did not close themselves: *1* is as many reviews as pull
   requests, *0.5* half as many and *2* twice as many. The cell shows the
   number of the author. The reviews given and the ratio have the same switches
   *Which reviews count* as the column *Reviews*. See
   :doc:`/reference/states/index`.
**Type of author**
   The author is an *owner* of the repository, a *member* of its organization,
   a *collaborator*, a *contributor* with earlier contributions, or a
   *first-timer*, whose first contribution it is; switch on the types that the
   column is about. GitHub tells the type with each pull request. The types are
   exclusive: an author has exactly one type for a pull request, the most
   privileged, so inverting the column switches on the other types. The cell
   shows the type. See :doc:`/reference/conditions/author_type`.
**Text**
   The title or the description of the pull request *starts with*, *ends
   with*, *contains* a text, or *matches the regex*, such as ``^(fix|feat):``;
   the case of letters does not matter unless *Case sensitive* is on. A regex
   has at most 100 characters; repetitions of groups that repeat themselves,
   such as ``(a+)+``, are refused, as they can take very long. See
   :doc:`/reference/conditions/text_matches`.
**Dashboard**
   Data of dashboard.pycal.org, not of GitHub: *PR Sync on*, the pull requests
   with the Status Message of the project, see :ref:`pr-message`, and *a skipped
   step*, those that skip a step, skipped by a person or for their author. Its
   results are not kept in the cache, as they change without an update.

The header of a column is short: the label, struck through when it must be
absent, or the states chosen, such as *conflict*. Below it, the gear changes
the column, moves it or removes it, and two toggles filter the table at once:
the check mark shows the pull requests the condition applies to, the cross
those it does not apply to. One of them is always on: switching off the last
one switches the other one on. The filters are an *or*: a pull
request shows when any column that filters shows it; a column with both
toggles on does not filter. Drag a column onto another one to move it. The
columns of conditions stay right of the other columns. The address of the page
keeps them, so it can be bookmarked and shared; the JSON has the result of each
column for each pull request (``conditions``), see :doc:`/reference/json`. A
question mark means that the data of the pull request is not complete yet, such
as checks that were never read, or reviews of a repository without the GitHub
App. See :doc:`/reference/conditions/index`. The site keeps the results of the
columns until a repository of the project is updated, so the table opens fast
also with many pull requests.

The tabs of a project are always in this order: the overview, the public tabs,
then those of the collaborators.

.. _project-filters:

Filters
=======

**Save** next to the number of pull requests saves the columns of conditions
as a filter: their order and whether each shows the pull requests it applies
to, those it does not apply to, or both. The page of saving asks for a name,
unique in the project, and a description in Markdown, and lists the conditions
in two tables, with their long names, such as *Label needs review: present*:

*Quality checks*
   Whether each shows the pull requests it applies to or those it does not. They
   filter as an *or*. In a step, they are its quality checks: a pull request is in the
   step while one of them is not fulfilled, and leaves it when all of them are.
*Skip if*
   If any of these conditions apply to a pull request, the step is skipped for
   it, and the filter does not show it. The page of the pull request says
   *Skipped:* and the condition, and the tab *Steps* lists them as *Skipped if*.

Drag a condition from one table to the other, or use **To Skip if** and **To the
quality checks**. Each condition has its type, a quality check or Skip if, and its
switch: a condition switched off stays in its table, grayed out. A switch at each condition turns it off: it is grayed out and
stays a column of the table without filtering; when a filter is saved the
first time, every condition is on. Every condition can be inverted: **Invert**
next to a condition turns it into its opposite, such as *PR is not auto-merging*
for *PR is auto-merging* or *fewer than 2 reviews* for *at least 2*, also when it
is off or of Skip if. Where no other choice is the opposite, it becomes the
*NOT* of the condition, which holds exactly when the condition does not, such as
*NOT Text: title contains “WIP”*; the table shows *NOT* in its header, and the
address starts its column with ``not~``. **Invert** again gives it back, and
**Remove** removes it. For a condition that shows only
what it does not apply to, the page suggests its opposite where it is the same,
such as *label absent* for not *label present*; **Use it** switches it.

Dragging a condition and these buttons keep the name, the description and the
switches as you typed them, until you save.

.. _and-conditions:

Conditions joined by AND
------------------------

Drag a condition onto another one to join them by *AND*: they become one
condition of the step, which holds when all of them hold, such as *PR has the
label needs review and PR is open*. Drag another condition onto the AND to add
it. Where a dragged condition lands is highlighted: the whole AND, the single
condition that makes a new AND with it, or the gap between two conditions, which
has room to drop in between. Dropping a condition into a gap moves it there, also into
the other table or out of its AND; dropping it where you picked it up changes
nothing. Without JavaScript, **AND with the one above** joins a condition with
the condition above it, and **Out of the AND** takes it out.

The page shows an AND as a group, with the line *AND: All of these, as one
condition* and its conditions joined by *and* above them. In the table of pull
requests, its columns have the mark *AND* with its number.

- As a quality check, an AND keeps a pull request in the step while all of its
  conditions hold, each as it filters: *PR is open and PR does not have the
  label bug*. It is one quality check of the step, with one summary and one
  description on the tab *Steps*, one line in the message of the pull request,
  and it is skipped as one (see :ref:`skips`). Its default text is its
  conditions joined by *and*, and its evidence is that of all of them.
- As a condition of *Skip if*, an AND skips the step when all of its conditions
  apply.

A condition of an AND has its own switch, **Invert** and **Remove**; one that is
switched off is no part of the AND. The AND itself is not inverted. An AND of one
condition is none: taking out the last but one leaves a single condition. A
condition that goes to the other table leaves its AND, and dropping a condition
of one table onto an AND of the other gives it the type of the AND.

Changing a column in the table of pull requests, its check marks and crosses,
moving it and saving the filter keep it in its AND. In the address, the columns
of an AND start with its number, such as
``col=and1~labels~applies~present~needs+review&col=and1~status~applies~open``.

Conditions joined by OR
-----------------------

The head of an AND has the choice **All of them (AND)** or **Any of them
(OR)**. *Any of them* turns the AND into an *OR*: one condition of the step,
which holds when one of its conditions holds, such as *PR is a draft or PR has
the label WIP*. The page shows it at once; without JavaScript, **Change** next
to the choice shows it, and every other button and saving keep the choice, too.
*All of them* turns it back into an AND. Everything else is as for an AND: it
is dragged together, it is one quality check with one summary and description,
and as a condition of *Skip if*, it skips the step when one of its conditions
applies. Its default text joins its conditions by *or*, and its evidence is
that of the conditions that hold, or of all of them when none holds. In the
table of pull requests, its columns have the mark *OR* with its number, and in
the address, they start with ``or`` and its number, such as
``col=or1~status~applies~draft&col=or1~labels~applies~present~WIP``.

The tab *Filters*, public like the project, lists the saved filters with their
description. **+ New filter** opens the table of pull requests with its menu **+**
open, to add the first condition of a new filter. Opening a filter shows a
loading animation while it counts the pull requests it shows and those each of its
conditions applies to. It shows only the conditions in force: those that are
off are no part of the filter and appear only in the table of pull requests and
when the filter is edited. **Pull requests** opens them with the filter, and
**Edit** opens the page of saving. A filter that is a step has **Step:** and the
name of the step there, which opens it, for everyone who can read the project. The page of
a saved filter, *Edit the filter* and its name, has **Edit the conditions** at the top right,
which opens the table of pull requests with them, and **Step:** when it is a step. A saved
filter saves itself while you edit its name, its description and the switches, like a step.
The button next to its title says *✓ Saved*, turns while it saves, and says *Save* when the
conditions differ from those saved, such as after a change in the table: a click saves them.
**Save as a new filter** leaves the saved one as it was. The table of pull requests remembers which
filter it shows while its columns change, so that **Save** saves that filter
again, also on the way from a step and back. A name of another filter of the
project asks whether to replace that filter: **Replace** gives it these
conditions and this description, and its step stays. Writers and owners save
filters.

A filter names its labels; a label of that name in any repository of the
project counts, in any case. When a label is renamed on GitHub, it keeps its
id: the next update of the repository finds it under its new name and renames
it in the saved filters, too, so that they keep working. New labels and
renames come with the webhook ``label``, or with the hourly update.

.. _project-steps:

Steps
=====

The tab *Steps*, right of *Filters*, shows the steps that a pull request goes
through, from left to right: *Step 1 → Step 2 → Step 3*. Each step is a saved
filter. In a step, the conditions of its filter are called its *quality checks*: what
keeps a pull request in it, such as a conflict or a missing review, to be done
before it can be merged. A pull request is in the left-most step with a quality check
for it, a condition of the filter that applies, and in no step when none does.

There are no steps until they are made: **Make it a step** next to a filter on
the tab *Filters*, or the button **+** of the tab *Steps*, adds the filter as
the last step. Drag a step in the bar to move it, or use its arrows; steps more
to the left come first.

The address of a step is ``steps/?step_id=<id>``, such as
``/projects/icalendar/steps/?step_id=7``: the id stays when the steps move. For an
id that the project does not have, such as of a step that was removed, the page says so
and shows the steps it has.

A click on a step shows it below the bar, with **Edit the filter** at the top
right, which opens the page of saving its filter. Its name is that of its filter
until you change it, and its summary is a template in Markdown. A click on a
quality check opens its summary, a line of text, and its description, which guides
people to do it, such as with a link to the documentation; the description is
written in the editor of Markdown, too. They take variables: the menu
**Variables** in the bar of the editor inserts the one you click where the
cursor is, see :ref:`step-variables`. **Preview** shows the text with an example
pull request, and says so when it uses variables. A step saves itself while you
edit it.

*Color* gives the step a color, the background of its box in the bars of the
steps, or none. The switch *Visible in the page of a pull request*, on by
default, shows the step in the bar of that page; switched off, the step shows
there only when the pull request is in it, and the bar of the tab *Steps*
marks it *hidden*. Who only reads the project sees the visible steps
only, each with **Filter:** and the name of its filter, which opens its pull requests.

Below the quality checks, *Skip conditions* has what makes a pull request skip
the step: the conditions *Skip if* of its filter, as *Skipped if*, and the
field *Skipped for these authors*, see below. After them, *Labels* has the labels that the GitHub App adds and removes
*when a pull request enters the step* and *when a pull request leaves the
step*: labels of the repositories or new ones, which GitHub then creates,
separated by commas, such as *triage, needs review*. A label renamed on GitHub
is renamed there, too. A pull request enters a step when an update finds it in
the step and it was in another one or in none before; it leaves a step when an
update finds it no longer in the step, while it is open, with all quality checks of the
step done, or because the step was skipped for it while it was in it.
dashboard.pycal.org remembers the step of each open pull request at every
update; the first time it sees a pull request, it only remembers where it is,
so nothing happens for steps entered or left before. The log records every
label added or removed.

.. _status-labels:

Step labels
-----------

The tab *Status Label* of *PR Sync*, see :ref:`pr-message`, switches the step
labels on and off. It is a table of the choices with what each means; choosing
another one says above **Apply** what Apply does:

*Off*, by default
   No step labels on GitHub. Apply deletes the labels of the steps from the
   repositories, such as *Delete the labels Review from
   collective/icalendar*, so only the owners switch them off.
*Synchronize*
   The steps have labels on GitHub. People put them on pull requests by hand,
   and dashboard.pycal.org puts the label of the step on the pull requests with
   the PR Sync on. Apply creates the labels and labels those pull requests, such
   as *Create the labels Review and label 3 pull requests*.

Each step then has a label in each repository with the GitHub App, with the name
of the step, such as *Review*: with the color of the step, the gray of GitHub for
a step without a color, and the description *Created by dashboard.pycal.org* with
the link to the step, ``steps/?step_id=<id>``. dashboard.pycal.org creates the
label, or takes one of that name, and changes it when the step changes. A label
renamed or recolored on GitHub renames or recolors the step. Labels made before
with the prefix *Step:*, such as *Step: Review*, are renamed to the name of the
step at the next update.

A label of a step that a person adds puts the pull request into that step. When
a pull request has two labels of steps or more, the one added last stays and
dashboard.pycal.org removes the others. When all of them are removed, the pull
request is in the step of its conditions again. The message follows the step, and
the log records every label created, added, removed or deleted. A removed step
keeps its label on GitHub.

**Check** next to the button **+** lists the pull requests outside of the
steps: no quality check of any step applies to them, so a filter of a step may lack a
condition for them. It lists the open pull requests, or all of them, also the
closed and merged ones, which are mostly outside as they are done.

.. _pull-request-page:

The page of a pull request
--------------------------

The title of a pull request in the table opens its page,
``/projects/<slug>/pull/<number>/``, public like the project. When several
repositories of the project have a pull request of the number, it asks which.
At the top, a bar shows every step of the project in its order, with its name
and a square for each quality check. The steps the pull request went through, left of
the step it is in, have a green border and a check mark. The step it is in, the
left-most one with a quality check to do, says so and shows how many of its quality checks are
done, such as *1/3*: its squares are green for a quality check done, on the left, and red
for a quality check to do, on the right, gray while its data is not known yet; its
border is yellow when some quality checks are done and red when none is. The steps after
it are gray, without numbers. Hidden steps are left out, unless the pull request
is in one. The step shown below the bar has a darker background. When no quality check of any
step applies to the pull request, all steps are gray and a note says that it is
outside of the usual steps it should take, such as a merged pull request.
The boxes of the steps are aligned in rows, as in a table: the names, the quality checks, *The pull
request is here*, the skip and the buttons.

Writers and owners skip a step for a pull request: **Skip** below the step opens a dialog
that asks why the step can be skipped, see :ref:`skips`. The pull request is then in the next step that shows
it; the skipped step is gray with a dashed border and still shows its quality checks, and its actions do
not follow. In the row of *The pull request is here*, everybody sees *Skipped by* and who
skipped it, linked to their page in the project; the writers and owners also see the reason,
such as *Skipped by @niccokunzmann: Reviewed at the meeting*. **Don't skip** undoes it. A step also skips itself
for the pull requests of the authors that its editor names under *Skip conditions*, in
*Skipped for these authors*, such as the maintainers, see :ref:`github-handles`: such a skip says *Skipped*
and names nobody.

A click on a step shows its summary and its quality checks below the bar. The quality checks to do
come first, marked *TODO* and open, with their description; the quality checks done have
a green check mark and are closed, and those skipped are gray, with ⏩ and who
skipped them.
Writers and owners skip a quality check with **Skip** in it, see :ref:`skips`. The summaries and descriptions show the
values of the pull request in place of the variables.

Each quality check shows the evidence of its condition: the least that shows why it holds
or not, as links. The checks of a passing or failing CI open on GitHub
(``/checks``); for an unknown CI, the reason, such as that the pull request is
closed or merged, and the pull request. A conflict, an outdated or up-to-date
branch and auto-merge open the box at the bottom of the pull request where it is
merged; GitHub gives that box no id that stays the same, so the link goes to the
box of comments right below it. Open, closed, merged and labels open the pull
request. Reviews show as many reviews as decide the condition: when 4 are
needed and 3 are there, those 3; for at most 2, three when there are more, else
all of them. The review to pull request ratio and the other states of the
author open the page of the author in the project.

.. _contributor-page:

The page of a person in a project
---------------------------------

``/projects/<slug>/contributors/<handle>/``, public like the project, shows a
person of GitHub in the repositories of the project that you see, with tabs:
*Profile* has what the conditions of the author count (reviews given, pull
requests opened, own pull requests closed and the review to pull request
ratio), and *Reviews*, *Issues* and *Pull requests* list them with their
counts, the newest first. The handle is that of GitHub, in any case. When the
person took no part in the project, the address leads to their page in all
projects.

.. _person-page:

The page of a person
--------------------

Every GitHub handle on the pages of the dashboard, such as the author of a
pull request, leads to the page of the person: in a project, to their page in
the project, else to ``/people/<handle>/``. The mark of GitHub right after the
handle leads to their profile on GitHub instead.

``/people/<handle>/`` lists the projects that you see in which the person
opened issues or pull requests, reviewed the pull requests of others or skipped
a step, with how many of each, and links to their page in each project. Every
GitHub handle has this page: one that took part in none of your projects shows
no GitHub name, so that it tells nothing of private repositories.

.. _pull-request-badge:

The badge of a pull request
---------------------------

Each pull request has a badge with the step it is in and how many of its quality checks
are done of all of them, such as *Triage 3/4*, with the color of the step behind
its name; *Steps: outside* when no quality check
of any step applies, and
*Steps: none* without steps. It is at the address of its page with
``badge.svg``, or ``badge.png`` for places that show no SVG, such as
``/projects/icalendar/pull/42/badge.svg``; when several repositories of the
project have pull requests, the address names the repository with
``?repository=collective/icalendar``. A badge is always a link to the page of
its pull request. The column *Step* of the table of pull requests shows it,
and the variable ``{pr_badge}`` puts it into a summary or description.

The site draws a badge once and keeps it until the repositories are updated or
the steps change; browsers and GitHub keep it for five minutes and then ask
whether it changed. The badge of a private repository is seen only by the
collaborators of its project, like the repository.

.. _step-variables:

Variables of the templates
--------------------------

The summary of a step and the descriptions of its quality checks take these variables,
in their groups. The examples are those of a pull request of
``collective/icalendar``; the page of a step shows its templates with them.


.. list-table:: Pull request
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{pr_title}``
     - The title of the pull request
     - ``Fix the time zones``
   * - ``{pr_number}``
     - The number of the pull request
     - ``42``
   * - ``{pr_url}``
     - The address of the pull request on GitHub
     - ``https://github.com/collective/icalendar/pull/42``
   * - ``{pr_merge_box}``
     - The address of the merge box of the pull request on GitHub, at the end
       of its conversation: its checks, its conflicts and the button to merge
       it, which people who signed in to GitHub see. Such as
       ``[Merge it]({pr_merge_box})``
     - ``https://github.com/collective/icalendar/pull/42#partial-pull-merging``

.. list-table:: Badge
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{pr_badge}``
     - The badge of the pull request in Markdown, linked to its page with its
       steps: ``[![View progress]({pr_badge_url})]({pr_steps_url})``, made of
       the addresses of the site, which are not escaped. Its alternative text,
       which screen readers read, is that of the badge on the pages of the
       dashboard, such as *Triage 3/4*; in the PR message it is *View
       progress*, as the comment stays on a pull request that leaves its scope
       while the badge goes on changing
     - ``[![View progress](https://dashboard.pycal.org/projects/icalendar/pull/42/badge.svg?repository=collective%2Ficalendar)](https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar)``
   * - ``{pr_badge_url}``
     - The address of the badge of the pull request, see
       :ref:`pull-request-badge`
     - ``https://dashboard.pycal.org/projects/icalendar/pull/42/badge.svg?repository=collective%2Ficalendar``
   * - ``{pr_steps_url}``
     - The address of the page of the pull request with its steps on
       dashboard.pycal.org, see :ref:`pull-request-page`
     - ``https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar``
   * - ``{pr_message_url}``
     - The fixed address of the PR message on dashboard.pycal.org: it leads to
       the Status Message on the pull request on GitHub, see :ref:`pr-message`,
       and to the pull request while it does not have the message. It stays the
       same, also when the comment is written again. Such as
       ``[The status]({pr_message_url})``
     - ``https://dashboard.pycal.org/projects/icalendar/pull/42/message/?repository=collective%2Ficalendar``

The addresses always name the repository of the pull request, so they stay the
same when the project gets another repository with a pull request of the same
number. In the message of the PR Sync, the address of the badge ends with
``&_v=`` and a number that changes with what the badge shows, its step and the
quality checks done: GitHub keeps images by their address, so it loads the badge again
when the step changes.

.. list-table:: Author
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{author_mention}``
     - Who opened the pull request, mentioned
     - ``@niccokunzmann``
   * - ``{author_name}``
     - The GitHub name of who opened it, else their GitHub handle
     - ``Nicco Kunzmann``
   * - ``{author_handle}``
     - The GitHub handle of who opened it
     - ``niccokunzmann``

.. list-table:: Repository
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{repository_name}``
     - The name of the repository
     - ``icalendar``
   * - ``{repository_full_name}``
     - The account and the name of the repository
     - ``collective/icalendar``
   * - ``{repository_owner}``
     - The account of the repository
     - ``collective``

.. list-table:: Project
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{project_name}``
     - The name of the project
     - ``iCalendar``

.. list-table:: Step
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{step_name}``
     - The name of the step
     - ``Review``
   * - ``{step_number}``
     - The place of the step, counted from 1
     - ``2``
   * - ``{step_id}``
     - The id of the step
     - ``7``

.. list-table:: Skip
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{step_skip_url}``
     - The address that opens the dialog to skip the step for the pull request
       on dashboard.pycal.org, for the writers and owners of the project. Such
       as ``[Skip this step]({step_skip_url})``, see :ref:`skips`
     - ``https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar&step=7&skip=step``
   * - ``{step_skip_url_author}``
     - The same address with a secret key, with which the author of the pull
       request may skip the step, too
     - ``https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar&step=7&skip=step&key=0123456789abcdef0123``
   * - ``{quality_check_skip_url}``
     - In the summary and the description of a quality check: the address that
       opens the dialog to skip it, for the writers and owners of the project
     - ``https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar&step=7&skip=reviews~applies~2``
   * - ``{quality_check_skip_url_author}``
     - In the summary and the description of a quality check: the same address
       with a secret key, with which the author of the pull request may skip
       it, too
     - ``https://dashboard.pycal.org/projects/icalendar/pull/42/?repository=collective%2Ficalendar&step=7&skip=reviews~applies~2&key=0123456789abcdef0123``

.. list-table:: Message
   :header-rows: 1
   :widths: 25 45 30

   * - Variable
     - Its value
     - Example
   * - ``{step_description}``
     - The summary of the step the pull request is in, in Markdown, with its
       variables
     - ``Thanks, @niccokunzmann! A person reviews it soon.``
   * - ``{tasks_all}``
     - All quality checks of the step, as a numbered list: those to do first, with
       ``:x:``, those not known yet with ``:grey_question:``, those done at the
       bottom, with ``:heavy_check_mark:``, and after them those skipped, with
       ``:fast_forward:`` (⏩), emoji that GitHub shows; the
       description of each quality check on the lines below it, indented, so that it
       belongs to its item
     - | ``1. :x: Solve the conflict``
       | ``2. :heavy_check_mark: Review it``
       | ``3. :fast_forward: Update the changelog``
   * - ``{tasks_todo}``
     - The quality checks to do; *Nothing to do.* when there are none
     - ``1. :x: Solve the conflict``
   * - ``{tasks_done}``
     - The quality checks done, then those skipped; *Nothing is done yet.* when
       there are none
     - | ``1. :heavy_check_mark: Review it``
       | ``2. :fast_forward: Update the changelog``

The variables of the group *Message* are for the message of the tab
*PR Sync* only, see :ref:`pr-message`; in a pull request in no step, the
variables of the step are empty.

The values are text: a title such as ``[click](https://example.org)`` stays
text, and nothing else of a template is evaluated; a name in braces that is not
a variable stays as it is. The badge, the description of the step and the
quality checks are Markdown, made by the site and the writers of the project.

.. _pr-message:

PR Sync
=======

The tab *PR Sync*, right of *Steps*, has the tabs *Current Message*, *Edit* and
*Preview* side by side, as they belong together, *Status Label*, the step labels,
see :ref:`status-labels`, and *Synchronization*. *Edit*, *Preview* and
*Synchronization* are for writers and owners.

The message of the project is the Status Message: the GitHub App writes it as a
comment on pull requests, and updates the comment whenever the message or the
values of its variables change, such as when a pull request enters the next step.
It is off until its scope says which pull requests get it.

There are two messages: the current one, which the pull requests get, and the
edited one, which is saved while it is written, also when you open the page
again later, and which the pull requests do not get before it is applied.

**Current Message**
   The message as a pull request gets it, with the tabs *Message*, *Markdown*
   and *Edit* above it, and below it which pull request it is of, such as *This
   is the message as it would appear in pull request collective/icalendar#42*,
   which links the message on that pull request on GitHub to check it there (the
   pull request while it does not have the message yet); and which pull requests
   get it; or that there is none yet. Everybody who sees the project
   steps through its examples here, as on *Preview*, and sees the message of a
   pull request by its number.
**Edit**
   The edited message in the editor of Markdown, with the menu **Variables**:
   those of the steps, see :ref:`step-variables`, and those of the group
   *Message*, such as the tasks of the step as a list of tasks of GitHub. It is
   saved while you write; without JavaScript, **Save** saves it.
**Preview**
   The edited message as example pull requests get it. Each example is in
   another state: another step, or another quality check done, to do or not known yet.
   They go from no quality check done to all of them: **→** shows the next one, **←**
   the one before, such as *Example 2 of 6: Review, 1 of 5 quality checks done*.
   **Show** shows the message of a pull request by its number instead. **Edit
   this step** opens the step that the pull request is in, with **Back to the
   review of the message** at the top.

*Edit* and *Preview* end with **Apply**, which applies the edited message and
synchronises it with the pull requests of the selection: the comments follow in
the background. Next to it, **Preview** on *Edit* and **Edit** on *Preview* go to
the other one. When the edited message is the
current one, the button says **✓ Applied**, in green. While they differ, the
other tabs say so, with **Continue editing**.

**Synchronization** has the *Pull request selection*: which pull requests get
the message, and with it the step labels. Its *Options*:

- *Add to these pull requests:* the pull requests of the numbers in the field,
  such as *2166, 2167*, or *collective/icalendar#42* where several repositories
  have the number; on by default;
- *Add to the open pull requests of these people:* the pull requests of the
  GitHub handles in the field, such as ``octocat, monalisa``: those open now and
  those they open later, but not the closed and merged ones. While you type,
  the field proposes GitHub handles, the authors of the pull requests of the
  project first, see :ref:`github-handles`. On by default;
- *Add to all new pull requests*: those opened after the switch was switched on;
- *Add to all open pull requests*;
- *Add to closed and merged pull requests*, in light red: not preferred, as they
  are done and their people get a notification.

**Keep X pull requests synchronized** saves the selection: the comments are written or updated
in the background, after an update of the project, and every update after it
updates those whose text changed. The number follows the switches; without
JavaScript, **Count** counts them. The log records every comment written or
updated; the comment ends with a hidden line that says that dashboard.pycal.org
wrote it.

.. _github-handles:

GitHub handles
==============

Every field of GitHub handles proposes people the same way while you type, by
their GitHub handle or GitHub name, with their avatar: in a project, the authors
of its pull requests first; then the people that dashboard.pycal.org knows and
that you may see: those who signed in, and the authors and reviewers of the
repositories of public projects and of your projects; then, from two
characters on and while fewer than ten are found, the accounts of all of
GitHub, which dashboard.pycal.org asks with your sign-in of GitHub and does not
keep. The field of the roles proposes only the people who signed in, as only
they can get a role, see :ref:`project-roles`. Without JavaScript, a field takes
the GitHub handles as you type them.

.. _project-settings:

Settings
========

The tab *Settings*, for writers and owners, has a second row of tabs:

*Display*
   The name, the description, the visibility and the address of the project.
*Repositories*
   The repositories of the project: add and remove them, see
   :ref:`add-repositories`. Everybody who sees the project sees its
   repositories on the tab *Overview*, the private ones only its collaborators.
*Collaborators*
   Who may do what in the project, see :ref:`project-roles`.
*Snapshots*
   Backups kept on dashboard.pycal.org, see :ref:`snapshots`.
*Backup*
   Download a backup, or restore one, see :ref:`project-backup`.
*Danger zone*
   In red: the owners delete the project. Its repositories stay on GitHub and
   in other projects; download a backup before, to keep the rest.

.. _snapshots:

Snapshots
=========

A snapshot is the backup of the project at a moment, kept on
dashboard.pycal.org. **Take a snapshot** on the tab *Settings → Snapshots*
keeps one; the list shows each with when it was taken and by whom, the newest
first, and the project keeps the newest 100. **Download** saves it as the file
of a backup, which restores as one. The owners **Restore** a snapshot as a
backup, with the same page of what it changes, and **Delete** it. Writers take
and download snapshots; deleting a project deletes its snapshots.

Two snapshots compare line by line, such as with ``diff old.yaml new.yaml``:
the file is sorted inside, so only what changed differs.

.. _project-backup:

Backup
======

The settings of a project have *Backup*, for writers and owners. **Download the
backup** saves a file of YAML with all that the people of the project decided:
its name and description, repositories, filters, steps with the skips of pull
requests, message and roles, see :doc:`/reference/backup`. **Show what the
backup changes**, for the owners only, reads such a file and shows what it adds
and what it would delete or replace, each with a box that is not ticked: a
filter added after the backup stays unless you tick its deletion. **Restore the
backup** then adds what the project lacks and makes what you ticked; the
visibility and the address stay as they are.

.. _project-roles:

Roles in a project
==================

On the tab *Settings → Collaborators*, the owners share the project with other people by
their GitHub handle, such as *niccokunzmann*: the field proposes the people who
signed in, by their GitHub handle or GitHub name, such as *Nicco Kunzmann*,
with their avatar, see :ref:`github-handles`. The person must have signed in to
dashboard.pycal.org once. What each role may do:

.. list-table::
   :header-rows: 1

   * - Action
     - Visitor
     - Read
     - Change
     - Own
   * - See a public project
     - yes
     - yes
     - yes
     - yes
   * - See a private project and private repositories
     - no
     - yes
     - yes
     - yes
   * - Update it from GitHub
     - no
     - yes
     - yes
     - yes
   * - Change the name, the description and the repositories
     - no
     - no
     - yes
     - yes
   * - Change the filters, the steps and the message
     - no
     - no
     - yes
     - yes
   * - See the collaborators and the settings, download a backup, take and download
       snapshots
     - no
     - no
     - yes
     - yes
   * - Add collaborators, change and remove their roles
     - no
     - no
     - no
     - yes
   * - Make it public or private, change its address
     - no
     - no
     - no
     - yes
   * - Restore a backup or a snapshot, delete a snapshot, delete the project
     - no
     - no
     - no
     - yes

Readers change nothing in the project, but update it from GitHub. Writers see
the tab *Settings*: they see who the collaborators are, take snapshots, but
invite nobody, and they do nothing destructive. Only the owners add
collaborators, change or remove their roles, decide who sees the project, and
delete it or replace its filters and steps with a backup. A project always has an owner: the only owner can neither change their role
nor leave until they give another person the role *own*. The administrators of the site (``SITE_ADMINS``) have the rights
of an owner in every project.

The JSON
========

Public projects have their JSON, such as ``/projects.json`` and
``/projects/icalendar.json``, see :doc:`/reference/json`.

.. list-table:: The pages of a project
   :header-rows: 1

   * - Page
     - Address
   * - Overview
     - ``/projects/<address>/``
   * - Pull requests
     - ``/projects/<address>/pull-requests/``
   * - Settings
     - ``/projects/<address>/settings/``, and its tabs
       ``settings/repositories/``, ``settings/collaborators/``,
       ``settings/snapshots/``, ``settings/backup/`` and ``settings/danger/``
