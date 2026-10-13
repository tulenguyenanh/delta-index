"""Title -> filename slug.

NFKD-normalize, fold to ASCII, lower-case, and collapse every run of
non-``[a-z0-9]`` to a single ``-``. The result only ever contains ``[a-z0-9-]``,
so it is safe to use as a path segment. An empty result is returned as ``""``
and the caller supplies a fallback. Pure function — no I/O, no clock.
"""

from __future__ import annotations

import re
import unicodedata


def slugify(title: str) -> str:
    """Return the filename-safe slug for ``title`` (possibly empty)."""
    ascii_title = (
        unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
