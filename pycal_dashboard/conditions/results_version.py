"""The version of what the conditions compute from the same data.

Raise :data:`RESULTS_VERSION` with every change of what a condition gives for the same data,
such as a new default: the results kept in the cache (``ColumnResults``, the badges of pull
requests) are computed again instead of being shown as they were.
"""

# 1: the reviews of the author of a pull request on it do not count by default (kind ``own``)
RESULTS_VERSION = 1
