"""No-key chat tests: grounded citations and the null-grounding path.

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

GROUNDED = {
    "candidates": [
        {
            "content": {
                "role": "model",
                "parts": [{"text": "Paste the YouTube link into the YouTube app."}],
            },
            "groundingMetadata": {
                "groundingChunks": [
                    {
                        "retrievedContext": {
                            "customMetadata": [
                                {"key": "source_url", "stringValue": YOUTUBE_URL},
                                {"key": "article_id", "stringValue": "360051014713"},
                            ]
                        }
                    },
                    {
                        "retrievedContext": {
                            "customMetadata": [
                                {"key": "source_url", "stringValue": OTHER_URL},
                            ]
                        }
                    },
                    {
                        "retrievedContext": {
                            "customMetadata": [
                                {"key": "source_url", "stringValue": YOUTUBE_URL},
                            ]
                        }
                    },
                    {
                        "retrievedContext": {
                            "customMetadata": [
                                {"key": "source_url", "stringValue": THIRD_URL},
                            ]
                        }
                    },
                    {
                        "retrievedContext": {
                            "customMetadata": [
                                {"key": "source_url", "stringValue": FOURTH_URL},
                            ]
                        }
                    },
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


@respx.mock
def test_ask_binds_prompt_and_returns_capped_distinct_citations(gemini_client) -> None:
    route = respx.post(url__regex=GENERATE_URL).mock(
        return_value=httpx.Response(200, json=GROUNDED)
    )

    text, urls = ask(gemini_client, STORE, "How do I add a YouTube video?")

    assert text.startswith("Paste the YouTube link")
    # Distinct, order-preserving, capped at 3 (the 4th distinct URL is dropped).
    assert urls == [YOUTUBE_URL, OTHER_URL, THIRD_URL]
    assert len(urls) == 3
    assert FOURTH_URL not in urls

    body = route.calls[0].request.content.decode("utf-8")
    assert PROMPT_FRAGMENT in body  # ASST-01: verbatim prompt bound as system_instruction
    assert "fileSearch" in body  # docs-only file_search tool, no web tool


@respx.mock
def test_ask_without_grounding_returns_no_citations(gemini_client) -> None:
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
