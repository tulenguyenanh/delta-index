"""Pure-function tests for slug generation and front-matter emission."""

from __future__ import annotations

from src.scraper.frontmatter import front_matter
from src.scraper.slug import slugify


def test_slugify() -> None:
    assert slugify("How to Use YouTube with OptiSigns") == "how-to-use-youtube-with-optisigns"


def test_front_matter() -> None:
    article = {
        "id": "360051014713",
        "title": "How to Use YouTube with OptiSigns",
        "html_url": (
            "https://support.optisigns.com/hc/en-us/articles/"
            "360051014713-How-to-Use-YouTube-with-OptiSigns"
        ),
        "updated_at": "2020-06-27T21:04:27Z",
    }

    block = front_matter(article)

    assert block.startswith("---\n")
    assert "article_id: 360051014713\n" in block
    assert 'source_url: "https://support.optisigns.com/hc/en-us/articles/360051014713' in block
