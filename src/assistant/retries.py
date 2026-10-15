"""Bounded retry policy shared by every Gemini File Search call.

google-genai raises its own ``errors.APIError`` family, not httpx exceptions,
so a policy that names only httpx types never fires on a 429 or a 503 and one
transient blip fails the whole daily run. ``is_transient`` retries transport
failures, HTTP 429 and any 5xx; every other API error (400, 403, 404, ...)
surfaces on the first attempt, because retrying it cannot succeed.
"""

from __future__ import annotations

import httpx
from google.genai import errors
from tenacity import retry_if_exception, stop_after_attempt, wait_exponential


def is_transient(exc: BaseException) -> bool:
    """Return True when ``exc`` is worth retrying with backoff."""
    if isinstance(exc, (httpx.TransportError, httpx.HTTPStatusError)):
        return True
    if isinstance(exc, errors.ServerError):
        return True
    return isinstance(exc, errors.ClientError) and exc.code == 429


# Same bounded shape as src/scraper/zendesk.py: 5 attempts, exponential backoff
# capped at 30s, and the real error re-raised once the budget is spent.
RETRY = {
    "stop": stop_after_attempt(5),
    "wait": wait_exponential(multiplier=1, max=30),
    "retry": retry_if_exception(is_transient),
    "reraise": True,
}
