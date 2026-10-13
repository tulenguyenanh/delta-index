"""No-key upload/store tests driven through the real SDK under ``respx``.

``respx`` intercepts google-genai's httpx transport, so the real
``upload_to_file_search_store`` resumable-upload path is exercised offline.
Two magic headers are required (learned the hard way): the initiate response
must carry ``X-Goog-Upload-URL`` and the follow-up response must carry
``X-Goog-Upload-Status: final``.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import respx

from src.assistant import store as store_module
from src.assistant.corpus import CorpusDoc
from src.assistant.store import ensure_store
from src.assistant.uploader import upload_corpus

STORE = "fileSearchStores/test-store"
UPLOAD_URL = "https://generativelanguage.googleapis.com/upload/v1beta/files/upload-123"
DOCUMENT_NAME = f"{STORE}/documents/doc-1"
YOUTUBE = Path("data") / "articles" / "how-to-use-youtube-with-optisigns.md"
SOURCE_URL = (
    "https://support.optisigns.com/hc/en-us/articles/"
    "360051014713-How-to-Use-YouTube-with-OptiSigns"
)


def _youtube_doc() -> CorpusDoc:
    return CorpusDoc(
        article_id=360051014713,
        title="How to Use YouTube with OptiSigns",
        source_url=SOURCE_URL,
        updated_at="2026-09-24T14:52:18Z",
        slug="how-to-use-youtube-with-optisigns",
        path=YOUTUBE,
    )


@respx.mock
def test_upload_sends_source_url_metadata_and_returns_report(gemini_client) -> None:
    initiate = respx.post(url__regex=r".*uploadToFileSearchStore.*").mock(
        return_value=httpx.Response(
            200,
            headers={
                "X-Goog-Upload-URL": UPLOAD_URL,
                "Content-Type": "application/json",
            },
            json={},
        )
    )
    respx.post(UPLOAD_URL).mock(
        return_value=httpx.Response(
            200,
            headers={"X-Goog-Upload-Status": "final"},
            json={
                "name": f"{STORE}/operations/op-1",
                "done": True,
                "response": {"documentName": DOCUMENT_NAME},
            },
        )
    )

    report = upload_corpus(gemini_client, STORE, [_youtube_doc()])

    assert report.files == 1
    assert report.est_chunks >= 1
    assert report.document_names == {"how-to-use-youtube-with-optisigns": DOCUMENT_NAME}

    # The metadata is attached in the SAME upload call, not a later pass.
    body = initiate.calls[0].request.content.decode("utf-8")
    assert "customMetadata" in body
    assert '"key": "source_url"' in body
    assert SOURCE_URL in body


@respx.mock
def test_ensure_store_reuses_matching_display_name(gemini_client, monkeypatch) -> None:
    monkeypatch.setattr(store_module, "GEMINI_STORE_NAME", None)
    respx.get(url__regex=r".*fileSearchStores.*").mock(
        return_value=httpx.Response(
            200,
            json={
                "fileSearchStores": [
                    {
                        "name": "fileSearchStores/existing-1",
                        "displayName": "optibot-knowledge-base",
                    }
                ]
            },
        )
    )
    create = respx.post(url__regex=r".*fileSearchStores$").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "fileSearchStores/new-1",
                "displayName": "optibot-knowledge-base",
            },
        )
    )

    name = ensure_store(gemini_client, "optibot-knowledge-base")

    assert name == "fileSearchStores/existing-1"
    assert create.call_count == 0  # reused, not recreated


@respx.mock
def test_ensure_store_creates_when_none_matches(gemini_client, monkeypatch) -> None:
    monkeypatch.setattr(store_module, "GEMINI_STORE_NAME", None)
    respx.get(url__regex=r".*fileSearchStores.*").mock(
        return_value=httpx.Response(200, json={"fileSearchStores": []})
    )
    respx.post(url__regex=r".*fileSearchStores$").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "fileSearchStores/new-1",
                "displayName": "optibot-knowledge-base",
            },
        )
    )

    name = ensure_store(gemini_client, "optibot-knowledge-base")

    assert name == "fileSearchStores/new-1"


@respx.mock
def test_ensure_store_honors_full_name_override(gemini_client, monkeypatch) -> None:
    monkeypatch.setattr(store_module, "GEMINI_STORE_NAME", "fileSearchStores/override-9")
    list_route = respx.get(url__regex=r".*fileSearchStores.*").mock(
        return_value=httpx.Response(200, json={"fileSearchStores": []})
    )

    name = ensure_store(gemini_client, "optibot-knowledge-base")

    assert name == "fileSearchStores/override-9"
    assert list_route.call_count == 0  # override short-circuits the lookup
