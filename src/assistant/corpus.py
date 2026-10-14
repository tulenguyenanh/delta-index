"""Read the Phase-1 corpus and parse its front-matter into ``CorpusDoc``.

Phase 1 emits exactly four front-matter keys in a fixed order: ``article_id``
(unquoted int), ``title`` / ``source_url`` / ``updated_at`` (JSON-quoted
strings). Parsing therefore decodes a value with ``json.loads`` only when it
starts with a quote, so the bare ``article_id`` token stays a numeric string
and needs no YAML dependency.

Pure module — no network, no clock. It reads committed first-party files only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ARTICLES_DIR = Path("data") / "articles"


@dataclass(frozen=True)
class CorpusDoc:
    """One cleaned corpus article plus the provenance the upload needs.

    ``content_sha256`` is the article file's fresh digest, computed once in
    :func:`read_corpus` and read from here by every consumer (the upload's
    metadata and the delta classifier) — no consumer re-reads the file, so the
    value a run compares against can never diverge from the value it uploads.
    """

    article_id: int
    title: str
    source_url: str
    updated_at: str
    slug: str
    path: Path
    content_sha256: str


def parse_front_matter(md_path: Path) -> dict[str, str]:
    """Return the ``---``-delimited front-matter of ``md_path`` as a dict."""
    text = md_path.read_text(encoding="utf-8")
    _, block, _ = text.split("---", 2)
    fields: dict[str, str] = {}
    for line in block.strip().splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        fields[key.strip()] = json.loads(value) if value.startswith('"') else value
    return fields


def read_corpus(articles_dir: Path | None = None) -> list[CorpusDoc]:
    """Read every ``*.md`` file under ``articles_dir`` into ``CorpusDoc``.

    Documents are sorted by slug (the filename stem). An empty directory is a
    hard error rather than a silent empty upload.
    """
    directory = articles_dir if articles_dir is not None else ARTICLES_DIR
    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise ValueError(f"no Markdown articles found in {directory}")

    docs: list[CorpusDoc] = []
    for path in paths:
        fields = parse_front_matter(path)
        docs.append(
            CorpusDoc(
                article_id=int(fields["article_id"]),
                title=fields["title"],
                source_url=fields["source_url"],
                updated_at=fields["updated_at"],
                slug=path.stem,
                path=path,
                # The ONE place the fresh corpus hash is computed. Phase 1's
                # byte-stable writes are what make hash equality meaningful.
                content_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    return docs
