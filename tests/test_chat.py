"""No-key chat tests: grounded citations, dedup/cap, fallback, no-grounding.

``respx`` intercepts google-genai's httpx transport, so the real SDK drives a
mocked ``generateContent`` response.
"""

from __future__ import annotations

import httpx
import respx

from src.assistant.chat import ask, render

STORE = "fileSearchStores/test-store"
GENERATE_URL = r".*:generateContent.*"
PROMPT_FRAGMENT = "You are OptiBot, the customer-support bot for OptiSigns.com."

YOUTUBE_URL = (
    "https://support.optisigns.com/hc/en-us/articles/"
    "360051014713-How-to-Use-YouTube-with-OptiSigns"
)
OTHER_URL = "https://support.optisigns.com/hc/en-us/articles/360059386254"
THIRD_URL = "https://support.optisigns.com/hc/en-us/articles/360060202914"
FOURTH_URL = "https://support.optisigns.com/hc/en-us/articles/999"
FALLBACK_URI = "https://support.optisigns.com/hc/en-us/articles/777"


def _chunk(url: str) -> dict:
    """A grounding chunk carrying ``url`` as its ``source_url`` custom metadata."""
    return {
        "retrievedContext": {
            "customMetadata": [{"key": "source_url", "stringValue": url}]
        }
    }


GROUNDED = {
    "candidates": [
        {
            "content": {
                "role": "model",
                "parts": [{"text": "Paste the YouTube link into the YouTube app."}],
            },
            "groundingMetadata": {
                "groundingChunks": [
                    _chunk(YOUTUBE_URL),
                    _chunk(OTHER_URL),
                    _chunk(YOUTUBE_URL),  # repeat -> must be deduped
                    _chunk(THIRD_URL),
                    _chunk(FOURTH_URL),  # 4th distinct -> dropped by the cap
                ]
            },
        }
    ]
}

UNGROUNDED = {
    "candidates": [
        {
            "content": {
                "role": "model",
                "parts": [{"text": "I can only answer from the docs."}],
            }
        }
    ]
}

URI_FALLBACK = {
    "candidates": [
        {
            "content": {
                "role": "model",
                "parts": [{"text": "See the linked doc."}],
            },
            "groundingMetadata": {
                "groundingChunks": [
                    {"retrievedContext": {"uri": FALLBACK_URI, "title": "Some Doc"}}
                ]
            },
        }
    ]
}


@respx.mock
def test_dedup_and_cap(gemini_client) -> None:
    respx.post(url__regex=GENERATE_URL).mock(
        return_value=httpx.Response(200, json=GROUNDED)
    )

    _, urls = ask(gemini_client, STORE, "How do I add a YouTube video?")

    # Order-preserving, the repeated URL collapses to one, capped at 3.
    assert urls == [YOUTUBE_URL, OTHER_URL, THIRD_URL]
    assert urls.count(YOUTUBE_URL) == 1
    assert len(urls) == 3
    assert FOURTH_URL not in urls


@respx.mock
def test_ask_binds_prompt_and_file_search_tool(gemini_client) -> None:
    route = respx.post(url__regex=GENERATE_URL).mock(
        return_value=httpx.Response(200, json=GROUNDED)
    )

    ask(gemini_client, STORE, "How do I add a YouTube video?")

    body = route.calls[0].request.content.decode("utf-8")
    assert PROMPT_FRAGMENT in body  # verbatim prompt bound as system_instruction
    assert "fileSearch" in body  # docs-only file_search tool, no web tool


@respx.mock
def test_uri_fallback(gemini_client) -> None:
    """A chunk with no custom_metadata falls back to retrieved_context.uri."""
    respx.post(url__regex=GENERATE_URL).mock(
        return_value=httpx.Response(200, json=URI_FALLBACK)
    )

    _, urls = ask(gemini_client, STORE, "Which doc covers this?")

    assert urls == [FALLBACK_URI]


@respx.mock
def test_no_grounding(gemini_client) -> None:
    respx.post(url__regex=GENERATE_URL).mock(
        return_value=httpx.Response(200, json=UNGROUNDED)
    )

    text, urls = ask(gemini_client, STORE, "What is the capital of France?")

    assert urls == []
    assert text.startswith("I can only answer")
    assert render(text, urls) == text.rstrip()


def test_render_appends_article_url_lines() -> None:
    rendered = render("Answer body.", [YOUTUBE_URL, OTHER_URL])

    assert rendered.splitlines()[0] == "Answer body."
    assert f"Article URL: {YOUTUBE_URL}" in rendered
    assert f"Article URL: {OTHER_URL}" in rendered
