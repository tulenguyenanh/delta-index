"""Offline delta tests: classification, delete ordering, and entrypoint policy.

``classify`` is pure, so its tests need no transport at all — they use plain
in-memory document stand-ins. The ``apply_delta`` tests drive the real SDK
under ``respx`` (reusing ``tests/test_uploader.py``'s two-step
resumable-upload mock shape) so the delete-then-recreate ordering is asserted
against the actual HTTP calls, not a fake. The ``main`` tests cover the
``API_KEY`` alias and the missing-pinned-id FATAL policy.
"""

from __future__ import annotations

import hashlib
import importlib
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
import respx

import main as main_module
from src.assistant.corpus import CorpusDoc, read_corpus
from src.assistant.delta import DeltaCounts, DeltaPlan, apply_delta, classify

STORE = "fileSearchStores/test-store"
UPLOAD_URL = "https://generativelanguage.googleapis.com/upload/v1beta/files/upload-123"
DOCUMENT_NAME = f"{STORE}/documents/doc-1"
YOUTUBE = Path("data") / "articles" / "how-to-use-youtube-with-optisigns.md"


# --- classify is pure: in-memory stand-ins, no respx ---------------------------


@dataclass
class _FakeMetadata:
    """Stand-in for ``types.CustomMetadata`` (only two fields matter)."""

    key: str
    string_value: str


@dataclass
class _FakeDocument:
    """Stand-in for ``types.Document`` as ``classify`` sees it."""

    name: str
    display_name: str
    custom_metadata: list[_FakeMetadata]


def _doc(slug: str, sha: str = "fresh", updated_at: str = "2026-01-01T00:00:00Z"):
    return CorpusDoc(
        article_id=1,
        title="title",
        source_url="https://example.test/article",
        updated_at=updated_at,
        slug=slug,
        path=Path("data") / "articles" / f"{slug}.md",
        content_sha256=sha,
    )


def _existing(name: str, display_name: str, **metadata: str) -> _FakeDocument:
    return _FakeDocument(
        name,
        display_name,
        [_FakeMetadata(key, value) for key, value in metadata.items()],
    )


def test_classify_added_updated_skipped() -> None:
    """Three docs, three buckets, each keyed by slug; updated carries .name."""
    existing = {
        "a": _existing(f"{STORE}/documents/a", "a", content_sha256="fresh"),
        "b": _existing(f"{STORE}/documents/b", "b", content_sha256="stale"),
    }

    plan = classify([_doc("a"), _doc("b"), _doc("c")], existing)

    assert [doc.slug for doc in plan.added] == ["c"]
    assert plan.updated == [(_doc("b"), f"{STORE}/documents/b")]
    assert [doc.slug for doc in plan.skipped] == ["a"]


def test_classify_all_skipped_second_run() -> None:
    """Unchanged content: stored hash == fresh hash for every slug -> all skipped."""
    docs = [_doc(slug) for slug in ("a", "b", "c")]
    existing = {
        doc.slug: _existing(
            f"{STORE}/documents/{doc.slug}", doc.slug, content_sha256=doc.content_sha256
        )
        for doc in docs
    }

    plan = classify(docs, existing)

    assert plan.added == []
    assert plan.updated == []
    assert [doc.slug for doc in plan.skipped] == ["a", "b", "c"]


def test_classify_falls_back_to_updated_at() -> None:
    """No stored content_sha256 -> compare the stored updated_at (L2 rung)."""
    existing = {
        "a": _existing(f"{STORE}/documents/a", "a", updated_at="2026-01-01T00:00:00Z"),
        "b": _existing(f"{STORE}/documents/b", "b", updated_at="2025-01-01T00:00:00Z"),
    }

    plan = classify([_doc("a"), _doc("b")], existing)

    assert [doc.slug for doc in plan.skipped] == ["a"]
    assert plan.updated == [(_doc("b"), f"{STORE}/documents/b")]


def test_classify_no_metadata_treated_as_changed() -> None:
    """A document with no usable metadata is re-uploaded, never silently skipped."""
    existing = {"a": _existing(f"{STORE}/documents/a", "a")}

    plan = classify([_doc("a")], existing)

    assert plan.updated == [(_doc("a"), f"{STORE}/documents/a")]
    assert plan.skipped == []


# --- apply_delta mutates: real SDK under respx --------------------------------


def _mock_upload() -> respx.Route:
    """Register the two-step resumable-upload mock; return the initiate route."""
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
    return initiate


@respx.mock
def test_apply_delta_delete_before_upload(gemini_client) -> None:
    """The existing document is deleted BEFORE its replacement is uploaded."""
    delete = respx.delete(url__regex=r".*/documents/.*").mock(
        return_value=httpx.Response(200, json={})
    )
    initiate = _mock_upload()

    doc = read_corpus()[0]
    plan = DeltaPlan(updated=[(doc, f"{STORE}/documents/old-1")])

    counts = apply_delta(gemini_client, STORE, plan)

    assert counts == DeltaCounts(added=0, updated=1, skipped=0)

    # Ordering across routes is the point, not merely that both were called.
    order = [(call.request.method, str(call.request.url)) for call in respx.calls]
    delete_index = next(i for i, (m, _) in enumerate(order) if m == "DELETE")
    upload_index = next(
        i
        for i, (m, url) in enumerate(order)
        if m == "POST" and "uploadToFileSearchStore" in url
    )
    assert delete_index < upload_index

    # force=True is mandatory; the SDK serialises the bool as "True".
    assert "force=true" in str(delete.calls[0].request.url).lower()
    assert delete.call_count == 1
    assert initiate.call_count == 1


@respx.mock
def test_apply_delta_counts(gemini_client) -> None:
    """1 added + 1 updated + 1 skipped: one delete+upload and one upload."""
    delete = respx.delete(url__regex=r".*/documents/.*").mock(
        return_value=httpx.Response(200, json={})
    )
    initiate = _mock_upload()

    docs = read_corpus()
    updated_doc, added_doc, skipped_doc = docs[0], docs[1], docs[2]
    plan = DeltaPlan(
        added=[added_doc],
        updated=[(updated_doc, f"{STORE}/documents/old-1")],
        skipped=[skipped_doc],
    )

    counts = apply_delta(gemini_client, STORE, plan)

    assert counts == DeltaCounts(added=1, updated=1, skipped=1)
    assert delete.call_count == 1  # only the updated slug is deleted
    assert initiate.call_count == 2  # one re-upload (updated) + one add


# --- main.py policy -----------------------------------------------------------


def test_main_missing_id_raises(monkeypatch, capsys) -> None:
    """A missing pinned article prints a FATAL line and re-raises (never swallowed)."""

    def _boom(*_args, **_kwargs):
        raise ValueError("selected article ids missing from the fetched corpus: [99]")

    monkeypatch.setattr(main_module, "scrape", _boom)

    with pytest.raises(ValueError, match="missing from the fetched corpus"):
        main_module.main()

    assert capsys.readouterr().out.startswith("FATAL:")


def test_main_api_key_alias(monkeypatch) -> None:
    """API_KEY is aliased to GOOGLE_API_KEY, losing to an already-set value."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("API_KEY", "alias-key")

    importlib.reload(main_module)

    assert os.environ["GOOGLE_API_KEY"] == "alias-key"


def test_main_api_key_alias_does_not_shadow(monkeypatch) -> None:
    """An existing GOOGLE_API_KEY is never overwritten by API_KEY."""
    monkeypatch.setenv("GOOGLE_API_KEY", "real-key")
    monkeypatch.setenv("API_KEY", "alias-key")

    importlib.reload(main_module)

    assert os.environ["GOOGLE_API_KEY"] == "real-key"


def test_youtube_doc_hash_matches_file() -> None:
    """Sanity: the corpus hash the upload writes is the file's real digest."""
    assert hashlib.sha256(YOUTUBE.read_bytes()).hexdigest() == _corpus_doc_hash(
        "how-to-use-youtube-with-optisigns"
    )


def _corpus_doc_hash(slug: str) -> str:
    for doc in read_corpus():
        if doc.slug == slug:
            return doc.content_sha256
    raise AssertionError(f"slug not in corpus: {slug}")
