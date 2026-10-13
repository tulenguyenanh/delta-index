"""Orchestrator and CLI entrypoint.

Wires the whole path together: fetch -> select -> clean -> convert ->
front-matter -> slug -> write. This is the only module that writes to the
filesystem.

Usage::

    python -m src.scraper.pipeline                 # full corpus
    python -m src.scraper.pipeline --only <id>     # single article (repeatable)
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .clean import clean_html
from .convert import to_markdown
from .frontmatter import front_matter
from .selection import select
from .slug import slugify
from .zendesk import fetch_articles

ARTICLES_DIR = Path("data") / "articles"
MANIFEST_PATH = Path("data") / "manifest.json"


def slug_for(article: dict[str, Any], seen: set[str] | None = None) -> str:
    """Return the output slug for ``article``, disambiguating within ``seen``."""
    base = slugify(article["title"]) or f"article-{int(article['id'])}"
    if seen is not None:
        if base in seen:
            base = f"{base}-{int(article['id'])}"
        seen.add(base)
    return base


def write_article(article: dict[str, Any], seen: set[str] | None = None) -> Path:
    """Write one article to ``data/articles/<slug>.md`` and return the path."""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTICLES_DIR / f"{slug_for(article, seen)}.md"
    content = front_matter(article) + to_markdown(clean_html(article["body"]))
    # newline="\n": never emit CRLF, so a Windows run matches the Linux image
    # byte-for-byte and a re-run is byte-identical.
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    return path


def run(article_ids: list[int] | None = None) -> list[Path]:
    """Fetch, select, and write articles; emit the sha256 manifest.

    With ``article_ids`` unset the full pinned corpus is selected via
    :func:`selection.select` and ``data/manifest.json`` is (re)written. With a
    list of ids the tracer path is unchanged: those articles are written and no
    manifest is touched (a single-article run must not clobber the corpus
    manifest).
    """
    articles = fetch_articles()
    if article_ids is None:
        articles = select(articles)
    else:
        wanted = set(article_ids)
        articles = [article for article in articles if int(article["id"]) in wanted]
        articles.sort(key=lambda article: (article["created_at"], int(article["id"])))

    seen: set[str] = set()
    paths = [write_article(article, seen) for article in articles]

    if article_ids is None:
        write_manifest({path.stem: _sha256(path) for path in paths})
    return paths


def _sha256(path: Path) -> str:
    """Return the hex sha256 digest of ``path``'s exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(hashes: dict[str, str]) -> Path:
    """Write ``slug -> sha256`` as deterministic JSON to ``data/manifest.json``.

    ``sort_keys`` keeps the map's key order stable and ``newline="\\n"`` keeps a
    Windows run byte-identical to the Linux image, so re-running against
    unchanged upstream content yields a byte-identical manifest.
    """
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(hashes, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    return MANIFEST_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scrape OptiSigns support articles into clean Markdown."
    )
    parser.add_argument(
        "--only",
        type=int,
        action="append",
        metavar="ID",
        help="write only the given article id (repeatable)",
    )
    args = parser.parse_args(argv)

    for path in run(article_ids=args.only):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
