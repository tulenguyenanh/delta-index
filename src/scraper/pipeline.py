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
from pathlib import Path
from typing import Any

from .clean import clean_html
from .convert import to_markdown
from .frontmatter import front_matter
from .slug import slugify
from .zendesk import fetch_articles

ARTICLES_DIR = Path("data") / "articles"


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
    """Fetch, order by ``(created_at, id)`` ascending, and write every article."""
    articles = fetch_articles()
    if article_ids is not None:
        wanted = set(article_ids)
        articles = [article for article in articles if int(article["id"]) in wanted]
    articles.sort(key=lambda article: (article["created_at"], int(article["id"])))
    seen: set[str] = set()
    return [write_article(article, seen) for article in articles]


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
