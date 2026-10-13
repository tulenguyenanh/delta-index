"""Deterministic front-matter emitter.

Emits the four contract keys in a fixed order. Every string scalar is
JSON-quoted, which is a valid YAML subset and is unambiguous: a ``:``/``?``/
``#``/leading ``*`` in a title can never break the block or inject a key, and
``updated_at`` is never coerced into a YAML timestamp object. Pure function —
no I/O, no clock.
"""

from __future__ import annotations

import json
from typing import Any


def _quote(value: str) -> str:
    """JSON-quote a scalar (valid YAML, unambiguous)."""
    return json.dumps(value, ensure_ascii=False)


def front_matter(article: dict[str, Any]) -> str:
    """Return the ``---``-delimited front-matter block for ``article``."""
    article_id = int(article["id"])
    return (
        "---\n"
        f"article_id: {article_id}\n"
        f"title: {_quote(article['title'])}\n"
        f"source_url: {_quote(article['html_url'])}\n"
        f"updated_at: {_quote(article['updated_at'])}\n"
        "---\n\n"
    )
