"""FastAPI SSE endpoint for OptiBot.

Run with ``python -m uvicorn src.assistant.api:app --reload --port 8000``
(GOOGLE_API_KEY set) from the repo root, then ``cd ui && npm run dev``; the UI
never sees the key. This module is additive — ``chat.py``, ``store.py``, ``config.py`` and
``prompt.py`` are reused via relative imports, never modified.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types
from google.genai.errors import ClientError

from .chat import extract_source_urls
from .config import GEMINI_MODEL, STORE_DISPLAY_NAME
from .prompt import OPTIBOT_SYSTEM_PROMPT
from .store import ensure_store, make_client

# Fixed friendly error messages — never ``str(exc)`` verbatim (that could leak
# key/transport details into the browser).
_ERROR_NO_KEY = "OptiBot is unavailable: GOOGLE_API_KEY is not set on the backend."
_ERROR_UNAVAILABLE = "OptiBot is unavailable right now. Please try again in a moment."
_ERROR_QUOTA = "OptiBot has reached its daily Gemini quota. Please try again later."
_ERROR_MISSING_QUESTION = "Missing question."

_SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive"}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event: str, data: str | None = None) -> str:
    """Render one SSE block: an ``event:`` line, a ``data:`` line, blank line.

    ``data=None`` yields an empty ``data:`` line (used by ``done``); otherwise
    ``data`` is the already-JSON-string payload on the ``data:`` line.
    """
    data_line = "data: " if data is None else f"data: {data}"
    return f"event: {event}\n{data_line}\n\n"


def _error_stream(message: str) -> StreamingResponse:
    """A single-``error``-event SSE response for the non-streamable failures."""
    return StreamingResponse(
        iter([_sse("error", json.dumps(message))]),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


def stream_answer(
    question: str,
    client: genai.Client | None = None,
    store_name: str | None = None,
) -> Iterator[str]:
    """Yield the SSE blocks for a grounded answer to ``question``.

    Emits ``token`` blocks as the model streams, then one ``citations`` block
    (a JSON list of up to three distinct grounding URLs) and a ``done`` block.
    Any failure yields a single ``error`` block instead — never a traceback.
    """
    if "GOOGLE_API_KEY" not in os.environ:
        yield _sse("error", json.dumps(_ERROR_NO_KEY))
        return

    try:
        client = client or make_client()
        store_name = store_name or ensure_store(client, STORE_DISPLAY_NAME)
        stream = client.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=OPTIBOT_SYSTEM_PROMPT,
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_name]
                        )
                    )
                ],
            ),
        )

        # Grounding often arrives on a single chunk near the end, so union every
        # chunk's grounding chunks; null-guard each level (empty is a safe fallback).
        collected: list[Any] = []
        for chunk in stream:
            fragment = getattr(chunk, "text", None)
            if fragment:
                yield _sse("token", json.dumps(fragment))
            for candidate in getattr(chunk, "candidates", None) or []:
                grounding_metadata = getattr(candidate, "grounding_metadata", None)
                if not grounding_metadata:
                    continue
                for grounding_chunk in (
                    getattr(grounding_metadata, "grounding_chunks", None) or []
                ):
                    collected.append(grounding_chunk)

        aggregated = SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    grounding_metadata=SimpleNamespace(grounding_chunks=collected)
                )
            ]
        )
        urls = extract_source_urls(aggregated)
        yield _sse("citations", json.dumps(urls))
        yield _sse("done")
    except ClientError as exc:  # noqa: BLE001 — a 429 quota limit is non-sensitive and self-explanatory
        if exc.code == 429:
            yield _sse("error", json.dumps(_ERROR_QUOTA))
        else:
            yield _sse("error", json.dumps(_ERROR_UNAVAILABLE))
    except Exception:  # noqa: BLE001 — a friendly event, never str(exc)
        yield _sse("error", json.dumps(_ERROR_UNAVAILABLE))


@app.post("/api/chat")
async def chat(request: Request) -> StreamingResponse:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 — malformed JSON is not a streamable request
        return _error_stream(_ERROR_MISSING_QUESTION)

    if not isinstance(body, dict):
        body = {}

    question = body.get("question")
    if not question or not str(question).strip():
        return _error_stream(_ERROR_MISSING_QUESTION)

    return StreamingResponse(
        stream_answer(str(question)),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
