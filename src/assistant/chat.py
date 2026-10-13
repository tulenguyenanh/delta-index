"""Grounded OptiBot question answering with ``Article URL:`` citations.

Calls ``generate_content`` with the verbatim OptiBot system prompt and the
``file_search`` tool alone (docs-only — no web/search tool). Citations are read
from ``grounding_chunks[].retrieved_context`` — the ``source_url`` attached at
upload — and rendered as up to three ``Article URL:`` lines.
"""

from __future__ import annotations

import argparse
from typing import Any

from google import genai
from google.genai import types

from .config import GEMINI_MODEL, STORE_DISPLAY_NAME
from .prompt import OPTIBOT_SYSTEM_PROMPT
from .store import ensure_store, make_client

_MAX_CITATIONS = 3


def extract_source_urls(response: Any) -> list[str]:
    """Lift up to three distinct source URLs from a grounded response.

    Every Optional level (``candidates``, ``grounding_metadata``,
    ``grounding_chunks``, ``retrieved_context``, ``custom_metadata``) is
    null-guarded, so a response with no grounding yields an empty list rather
    than raising. Falls back to ``retrieved_context.uri`` / ``.title`` when a
    chunk carries no ``custom_metadata``.
    """
    urls: list[str] = []
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return urls
    grounding_metadata = getattr(candidates[0], "grounding_metadata", None)
    if not grounding_metadata:
        return urls

    for chunk in grounding_metadata.grounding_chunks or []:
        context = getattr(chunk, "retrieved_context", None)
        if not context:
            continue
        matched = False
        for metadata in context.custom_metadata or []:
            if metadata.key == "source_url" and metadata.string_value:
                matched = True
                if metadata.string_value not in urls:
                    urls.append(metadata.string_value)
        if not matched:
            fallback = context.uri or context.title
            if fallback and fallback not in urls:
                urls.append(fallback)
        if len(urls) >= _MAX_CITATIONS:
            break

    return urls[:_MAX_CITATIONS]


def ask(
    client: genai.Client,
    store_name: str,
    question: str,
    model: str = GEMINI_MODEL,
) -> tuple[str, list[str]]:
    """Ask ``question`` grounded only in the File Search store's documents."""
    response = client.models.generate_content(
        model=model,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=OPTIBOT_SYSTEM_PROMPT,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(file_search_store_names=[store_name])
                )
            ],
        ),
    )
    return response.text or "", extract_source_urls(response)


def render(text: str, urls: list[str]) -> str:
    """Append up to three distinct ``Article URL:`` lines to ``text``.

    The verbatim system prompt already asks the model to cite up to three
    ``Article URL:`` lines itself, so a grounding URL that the model has
    *already* written into its answer is not appended a second time — the same
    citation never appears twice. At most three distinct citations are shown in
    total, and only grounding-supplied URLs are ever appended (nothing is
    fabricated). When the model cited nothing, the grounding URLs supply the
    citation lines.
    """
    body = text.rstrip()
    # Grounding URLs the model already cited in its own answer text.
    already_cited = sum(1 for url in urls if url in body)
    # Append only distinct URLs the answer does not already contain, keeping the
    # overall distinct-citation count at or below the cap.
    budget = max(0, _MAX_CITATIONS - already_cited)
    appended: list[str] = []
    for url in urls:
        if len(appended) >= budget:
            break
        if url in body or url in appended:
            continue
        appended.append(url)
    lines = [body]
    lines.extend(f"Article URL: {url}" for url in appended)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ask OptiBot a question grounded in the uploaded docs."
    )
    parser.add_argument("question", help="the question to ask OptiBot")
    args = parser.parse_args(argv)

    client = make_client()
    store_name = ensure_store(client, STORE_DISPLAY_NAME)
    text, urls = ask(client, store_name, args.question)
    print(render(text, urls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
