"""The import guard: every lazy import, a module imported inside a function, goes through it.

The site imports some packages only when it needs them, such as httpx when it speaks with
GitHub, which keeps its memory low when idle. Threads that serve pages at the same time would
otherwise import parts of them at the same time, in another order, which Python's import can stop
as a deadlock. Every import inside a function therefore happens inside ``with IMPORT_GUARD:``, as
in community-insights; ``tests/quality/test_lazy_imports.py`` checks it.
"""

import threading

# one thread at a time imports lazily; re-entrant, as a lazy import may import lazily itself
IMPORT_GUARD = threading.RLock()
