"""Front-matter parser and corpus reader tests against a real corpus file.

No network: ``parse_front_matter`` / ``read_corpus`` read committed files only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.assistant.corpus import CorpusDoc, parse_front_matter, read_corpus

YOUTUBE = Path("data") / "articles" / "how-to-use-youtube-with-optisigns.md"
SOURCE_URL = (
    "https://support.optisigns.com/hc/en-us/articles/"
    "360051014713-How-to-Use-YouTube-with-OptiSigns"
)


def test_parse_front_matter_returns_the_four_contract_keys() -> None:
    fields = parse_front_matter(YOUTUBE)

    assert fields["article_id"] == "360051014713"  # raw numeric string, not an int
    assert fields["title"] == "How to Use YouTube with OptiSigns"
    assert fields["source_url"] == SOURCE_URL
    assert fields["updated_at"] == "2026-09-24T14:52:18Z"


def test_read_corpus_contains_the_youtube_doc() -> None:
    docs = read_corpus()
    by_slug = {doc.slug: doc for doc in docs}

    assert "how-to-use-youtube-with-optisigns" in by_slug
    doc = by_slug["how-to-use-youtube-with-optisigns"]
    assert isinstance(doc, CorpusDoc)
    assert doc.article_id == 360051014713
    assert doc.source_url == SOURCE_URL
    assert doc.path.name == "how-to-use-youtube-with-optisigns.md"
    assert [d.slug for d in docs] == sorted(d.slug for d in docs)


def test_missing_corpus(tmp_path: Path) -> None:
    """An empty articles directory is a hard error, not a silent empty upload."""
    empty = tmp_path / "articles"
    empty.mkdir()

    with pytest.raises(ValueError):
        read_corpus(empty)
