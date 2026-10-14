"""No-key API tests: SSE framing, grounding aggregation, empty citations, key gate.

No network, no real key — fake ``client`` objects drive ``stream_answer`` and
``TestClient`` exercises the HTTP route.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from google.genai.errors import ClientError

from src.assistant.api import app, stream_answer


def _grounding_chunk(url: str) -> SimpleNamespace:
    return SimpleNamespace(
        retrieved_context=SimpleNamespace(
            custom_metadata=[SimpleNamespace(key="source_url", string_value=url)]
        )
    )


def _chunk(text: str, urls: list[str]) -> SimpleNamespace:
    """A fake streamed chunk with incremental text and grounding metadata."""
    return SimpleNamespace(
        text=text,
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    grounding_chunks=[_grounding_chunk(url) for url in urls]
                )
            )
        ],
    )


def _fake_client(chunks: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(
        models=SimpleNamespace(
            generate_content_stream=lambda **kwargs: iter(chunks)
        )
    )


def _raising_client(exc: Exception) -> SimpleNamespace:
    def boom(**kwargs):
        raise exc

    return SimpleNamespace(models=SimpleNamespace(generate_content_stream=boom))


def test_missing_question_emits_error_event() -> None:
    client = TestClient(app)
    response = client.post("/api/chat", json={"foo": "bar"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: error" in response.text
    assert "event: token" not in response.text


def test_stream_answer_emits_token_citations_done() -> None:
    urls = ["https://a.example/1", "https://b.example/2"]
    client = _fake_client([_chunk("Hello ", [urls[0]]), _chunk("world", [urls[1]])])

    events = list(stream_answer("How do I?", client=client, store_name="fileSearchStores/test"))
    joined = "\n".join(events)

    assert "event: token" in joined
    assert "event: citations" in joined
    assert "event: done" in joined
    assert joined.index("event: token") < joined.index("event: citations")
    assert joined.index("event: citations") < joined.index("event: done")
    # The citations payload is the JSON list of grounding URLs.
    assert json.dumps(urls) in joined


def test_stream_answer_no_grounding_emits_empty_citations() -> None:
    client = _fake_client([SimpleNamespace(text="No docs.", candidates=[])])

    events = list(stream_answer("q", client=client, store_name="fileSearchStores/test"))
    joined = "\n".join(events)

    assert "event: citations" in joined
    assert "data: []" in joined


def test_stream_answer_missing_key_emits_error(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    events = list(stream_answer("q"))

    assert events[0].startswith("event: error")
    assert "GOOGLE_API_KEY" in events[0]


def test_stream_answer_quota_emits_quota_error() -> None:
    client = _raising_client(
        ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}})
    )

    events = list(stream_answer("q", client=client, store_name="fileSearchStores/test"))

    assert len(events) == 1
    assert events[0].startswith("event: error")
    assert "quota" in events[0].lower()
    assert "unavailable right now" not in events[0]


def test_stream_answer_other_client_error_emits_unavailable() -> None:
    client = _raising_client(
        ClientError(500, {"error": {"code": 500, "status": "INTERNAL"}})
    )

    events = list(stream_answer("q", client=client, store_name="fileSearchStores/test"))

    assert len(events) == 1
    assert events[0].startswith("event: error")
    assert "unavailable right now" in events[0]
    assert "quota" not in events[0].lower()
