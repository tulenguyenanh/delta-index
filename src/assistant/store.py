"""Gemini File Search store lifecycle: client factory and get-or-reuse.

Thin boundary adapter around the google-genai SDK. The API key is read only by
``genai.Client()`` (which pulls ``GOOGLE_API_KEY`` from the environment); the
key and the raw client are never logged.
"""

from __future__ import annotations

from typing import Any

import httpx
from google import genai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import GEMINI_STORE_NAME

# Same bounded-retry idiom as src/scraper/zendesk.py, applied to the store
# list/create calls so a transient transport error is retried with backoff.
_RETRY = {
    "stop": stop_after_attempt(5),
    "wait": wait_exponential(multiplier=1, max=30),
    "retry": retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    "reraise": True,
}


def make_client(client: genai.Client | None = None) -> genai.Client:
    """Return ``client`` when injected, else a fresh client from the env key."""
    if client is not None:
        return client
    return genai.Client()


@retry(**_RETRY)
def _list_stores(client: genai.Client) -> list[Any]:
    """List every File Search store visible to the API key."""
    return list(client.file_search_stores.list())


@retry(**_RETRY)
def _create_store(client: genai.Client, display_name: str) -> Any:
    """Create a new File Search store carrying ``display_name``."""
    return client.file_search_stores.create(config={"display_name": display_name})


def ensure_store(client: genai.Client, display_name: str) -> str:
    """Return the store NAME to upload into, reusing a store when possible.

    Precedence: an explicit ``GEMINI_STORE_NAME`` override wins; otherwise the
    first listed store whose ``display_name`` matches is reused; otherwise a
    new store is created and its name returned. Reuse is what stops the Phase 3
    daily job from orphaning a fresh store (and re-embedding the corpus) on
    every run.
    """
    if GEMINI_STORE_NAME:
        return GEMINI_STORE_NAME
    for store in _list_stores(client):
        if store.display_name == display_name:
            return store.name
    return _create_store(client, display_name).name
