"""The groups of conditions that the table of pull requests shows as columns, one per module.

A group (:class:`~.base.ConditionGroup`) bundles conditions for people: the labels (present or
absent), the branch (up to date, outdated, conflict), the CI (passing or failing) and the
status (open, closed, merged, auto-merging). A column of the table (:class:`~.column.Column`)
is a group with its choices and a filter.
"""
