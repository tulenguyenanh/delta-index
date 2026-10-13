"""No-network tests for cursor pagination and pinned corpus selection.

``respx`` intercepts the ``httpx`` transport, so the cursor walk is exercised
end-to-end (two pages, ``meta.has_more`` driving the loop) without touching the
network.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from src.scraper.selection import SELECTED_IDS, select
from src.scraper.zendesk import BASE, LOCALE, fetch_articles

ARTICLES_URL = f"{BASE}/{LOCALE}/articles"


def _article(article_id: int, created_at: str) -> dict[str, str]:
    return {
        "id": str(article_id),
        "title": f"Article {article_id}",
        "html_url": f"https://support.optisigns.com/hc/en-us/articles/{article_id}",
        "updated_at": "2020-01-01T00:00:00Z",
        "created_at": created_at,
        "body": "<p>hello</p>",
    }


def _thirty_selected() -> list[dict[str, str]]:
    """One article per pinned id, created_at ascending in ``SELECTED_IDS`` order."""
    return [
        _article(article_id, f"2021-01-{index + 1:02d}T00:00:00Z")
        for index, article_id in enumerate(SELECTED_IDS)
    ]


@respx.mock
def test_cursor_walk_two_pages() -> None:
    """Two pages; the loop stops as soon as ``has_more`` is false."""
    page_two = f"{ARTICLES_URL}?page[after]=cursor2&page[size]=100"
    route = respx.get(url__startswith=ARTICLES_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "articles": [_article(1, "2020-01-01T00:00:00Z"),
                                 _article(2, "2020-02-01T00:00:00Z")],
                    "meta": {"has_more": True},
                    "links": {"next": page_two},
                },
            ),
            httpx.Response(
                200,
                json={
                    "articles": [_article(3, "2020-03-01T00:00:00Z")],
                    "meta": {"has_more": False},
                    "links": {},
                },
            ),
        ]
    )

    articles = fetch_articles()

    assert [int(article["id"]) for article in articles] == [1, 2, 3]
    assert len(articles) == 3
    # Exactly two requests: no third request fired after has_more went false
    # (a third would exhaust the side_effect list and raise instead).
    assert route.call_count == 2
    assert "cursor2" in str(route.calls[1].request.url)


def test_select_returns_30_ordered_by_created_at() -> None:
    """select() filters out non-selected ids and orders by (created_at, id)."""
    selected = _thirty_selected()
    strangers = [_article(999001, "1999-01-01T00:00:00Z")]  # earliest, must be dropped
    shuffled = list(reversed(selected)) + strangers

    chosen = select(shuffled)

    assert len(chosen) == 30
    created = [article["created_at"] for article in chosen]
    assert created == sorted(created)
    assert [int(article["id"]) for article in chosen] == list(SELECTED_IDS)


def test_select_raises_when_selected_id_missing() -> None:
    """A missing pinned id is a hard error, never a silent shortfall."""
    incomplete = _thirty_selected()[:-1]  # drop one pinned id

    with pytest.raises(ValueError) as excinfo:
        select(incomplete)

    assert str(SELECTED_IDS[-1]) in str(excinfo.value)
