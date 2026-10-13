"""Pure-function tests for the transform path and its edge cases.

Covers slug generation, front-matter emission, iframe preservation, table-cell
images, the slug fallback/collision backstops, an empty body, and exact
``updated_at`` preservation. No network, no clock.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.scraper import pipeline
from src.scraper.clean import clean_html
from src.scraper.convert import to_markdown
from src.scraper.frontmatter import front_matter
from src.scraper.pipeline import slug_for, write_article
from src.scraper.slug import slugify


def _article(**overrides) -> dict[str, str]:
    article = {
        "id": "360051014713",
        "title": "How to Use YouTube with OptiSigns",
        "html_url": (
            "https://support.optisigns.com/hc/en-us/articles/"
            "360051014713-How-to-Use-YouTube-with-OptiSigns"
        ),
        "updated_at": "2020-06-27T21:04:27Z",
        "body": "<p>hello</p>",
    }
    article.update(overrides)
    return article


def test_slugify() -> None:
    assert slugify("How to Use YouTube with OptiSigns") == "how-to-use-youtube-with-optisigns"


def test_front_matter() -> None:
    block = front_matter(_article())

    assert block.startswith("---\n")
    assert "article_id: 360051014713\n" in block
    assert 'source_url: "https://support.optisigns.com/hc/en-us/articles/360051014713' in block


def test_iframe_converted_to_link() -> None:
    html = (
        "<p>Watch this video</p>"
        '<iframe src="https://www.youtube-nocookie.com/embed/X"></iframe>'
    )

    markdown = to_markdown(clean_html(html))

    assert "https://www.youtube-nocookie.com/embed/X" in markdown
    assert "[Embedded video](https://www.youtube-nocookie.com/embed/X)" in markdown


def test_table_cell_image_kept() -> None:
    html = (
        "<table><tr><td>"
        '<img src="https://x/y.png" alt="shot">'
        "</td></tr></table>"
    )

    markdown = to_markdown(clean_html(html))

    assert "https://x/y.png" in markdown
    assert "![shot]" in markdown


def test_slug_empty_fallback() -> None:
    # A title of only non-alphanumerics slugifies to "" -> article-{id} fallback.
    assert slugify("!!? --") == ""
    assert slug_for(_article(id="424242", title="!!? --")) == "article-424242"


def test_slug_collision_disambiguated() -> None:
    seen: set[str] = set()
    first = slug_for(_article(id="111", title="Same Title"), seen)
    second = slug_for(_article(id="222", title="Same Title"), seen)

    assert first == "same-title"
    assert second == "same-title-222"
    assert first != second


def test_empty_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "ARTICLES_DIR", tmp_path / "articles")
    article = _article(id="999", title="Empty Body", body="")

    path = write_article(article)
    text = path.read_text(encoding="utf-8")

    # Front-matter is complete; everything after it is just the empty body.
    block = front_matter(article)
    assert text.startswith(block)
    assert text[len(block):] == "\n"


def test_updated_at_preserved() -> None:
    timestamp = "2026-09-10T09:39:18Z"

    block = front_matter(_article(updated_at=timestamp))

    assert f'updated_at: "{timestamp}"' in block
