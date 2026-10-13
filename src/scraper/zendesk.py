"""Cursor-paginated, anonymous client for the Zendesk Help Center API.

This is the only module that performs network I/O. It walks the public Help
Center article list endpoint, following ``links.next`` while ``meta.has_more``
is true, and yields raw article dicts (the list response already includes each
article ``body``, so no per-article fetch is required).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

BASE = "https://support.optisigns.com/api/v2/help_center"
LOCALE = "en-us"

# Request-phase-specific timeout: a mid-body stall surfaces as a catchable
# httpx.ReadTimeout rather than an ambiguous connection error.
DEFAULT_TIMEOUT = httpx.Timeout(connect=10, read=30, write=10, pool=10)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, max=30),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    reraise=True,
)
def _get(client: httpx.Client, url: str) -> dict[str, Any]:
    """GET ``url`` as JSON, retrying transient transport/status errors."""
    response = client.get(url, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()


def iter_articles(client: httpx.Client) -> Iterator[dict[str, Any]]:
    """Yield every article dict, following the server cursor until exhausted."""
    url: str | None = f"{BASE}/{LOCALE}/articles?page[size]=100"
    while url:
        data = _get(client, url)
        yield from data["articles"]
        url = (data.get("links") or {}).get("next") if data["meta"]["has_more"] else None


def fetch_articles(client: httpx.Client | None = None) -> list[dict[str, Any]]:
    """Drain :func:`iter_articles` into a list, owning a client if none given."""
    if client is not None:
        return list(iter_articles(client))
    with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as owned:
        return list(iter_articles(owned))
