"""Offline delta tests: pure classification plus the delete-then-recreate path.

``classify`` is exercised with plain in-memory document stand-ins (no respx):
it is a pure function, so its test needs no transport. The ``apply_delta`` and
``main`` paths are driven through the real SDK under ``respx`` in the fuller
suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.assistant.corpus import CorpusDoc
from src.assistant.delta import classify


@dataclass
class _FakeMetadata:
    """Stand-in for ``types.CustomMetadata`` (only these two fields matter)."""

    key: str
    string_value: str


@dataclass
class _FakeDocument:
    """Stand-in for ``types.Document`` as ``classify`` sees it."""

    name: str
    display_name: str
    custom_metadata: list[_FakeMetadata]


def _doc(slug: str, sha: str = "fresh") -> CorpusDoc:
    return CorpusDoc(
        article_id=1,
        title="title",
        source_url="https://example.test/article",
        updated_at="2026-01-01T00:00:00Z",
        slug=slug,
        path=Path("data") / "articles" / f"{slug}.md",
        content_sha256=sha,
    )


def test_classify_smoke() -> None:
    """One added, one updated (hash differs), one skipped (hash matches)."""
    existing = {
        "a": _FakeDocument(
            "stores/s/documents/1", "a", [_FakeMetadata("content_sha256", "fresh")]
        ),
        "b": _FakeDocument(
            "stores/s/documents/2", "b", [_FakeMetadata("content_sha256", "stale")]
        ),
    }

    plan = classify([_doc("a"), _doc("b"), _doc("c")], existing)

    assert [doc.slug for doc in plan.added] == ["c"]
    assert plan.updated == [(_doc("b"), "stores/s/documents/2")]
    assert [doc.slug for doc in plan.skipped] == ["a"]
