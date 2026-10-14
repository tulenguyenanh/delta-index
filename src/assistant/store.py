"""Gemini File Search store lifecycle: client factory and get-or-reuse.

Thin boundary adapter around the google-genai SDK. The API key is read only by
``genai.Client()`` (which pulls ``GOOGLE_API_KEY`` from the environment); the
key and the raw client are never logged.

Besides the get-or-reuse store lifecycle it exposes the two document-level
boundaries the Phase 3 delta job needs: ``list_store_documents`` (the store's
own hashes, the comparison input for ``classify``) and ``delete_document``
(the delete half of delete-then-recreate for a changed slug).
"""

from __future__ import annotations

from typing import Any

import httpx
from google import genai
from google.genai import types
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


@retry(**_RETRY)
def _list_documents(client: genai.Client, store_name: str) -> list[Any]:
    """List every document in ``store_name``, fully iterating the Pager."""
    return list(client.file_search_stores.documents.list(parent=store_name))


def list_store_documents(client: genai.Client, store_name: str) -> dict[str, Any]:
    """Return ``{display_name: document}`` for the store's documents.

    The SDK's ``documents.list`` returns a ``Pager``; it is fully iterated here
    because the REST default page size is 10 (max 20) while the store holds 30.
    A single page would look like a 20-document shortfall and re-upload the
    rest, so ``next()`` is never used. Documents without a ``display_name``
    cannot be joined by slug and are skipped.
    """
    by_display_name: dict[str, Any] = {}
    for document in _list_documents(client, store_name):
        if document.display_name is not None:
            by_display_name[document.display_name] = document
    return by_display_name


@retry(**_RETRY)
def _delete_document(client: genai.Client, document_name: str) -> None:
    """Delete one document, forcing removal of its embedded chunks."""
    client.file_search_stores.documents.delete(
        name=document_name, config=types.DeleteDocumentConfig(force=True)
    )


def delete_document(client: genai.Client, document_name: str) -> None:
    """Delete ``document_name`` from its store.

    ``force=True`` is mandatory: the default fails ``FAILED_PRECONDITION``
    while the document still has embedded chunks. This is called before
    re-uploading a changed document so the store never holds two copies of a
    slug.
    """
    _delete_document(client, document_name)


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
