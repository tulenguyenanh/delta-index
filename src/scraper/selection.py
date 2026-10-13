"""Pinned, deterministic corpus selection.

The corpus for Phase 1 is a *pinned* list of 30 article ids, not a mechanical
``take 30`` of the API's default order. That distinction matters: the upstream
Help Center now exposes 415 ``en-us`` articles and a naive slice by recency
would silently drift every time a new article is published, and would omit the
article Phase 2's graded sanity question depends on
(``360051014713`` — "How to Use YouTube with OptiSigns").

``SELECTED_IDS`` is therefore the single source of truth: an immutable tuple of
30 ids, held in ``created_at``-ascending order (ids first published in 2019
through 2026, a representative spread rather than a recency slice). Because the
list is pinned rather than derived, a future publication cannot shift it.

Pure module — no I/O, no clock, no network.
"""

from __future__ import annotations

from typing import Any

# Exactly 30 ids, in created_at-ascending order. Do NOT regenerate this list by
# slicing the live corpus; it is the locked, coverage-aware selection (locked
# decision 1) and force-includes the YouTube article 360051014713.
SELECTED_IDS: tuple[int, ...] = (
    360016174554,
    360016380053,
    360020931734,
    360034379293,
    360039264133,
    360042424294,
    360047499893,
    360051014713,
    360052361293,
    360055080914,
    1500000480302,
    1500002131621,
    1500008112642,
    4403616315539,
    4407335862931,
    4411762539027,
    4416542923667,
    7592123111699,
    11116333259283,
    15313086319763,
    18986181635859,
    23030445716883,
    27607906766483,
    29238381023123,
    32272215514131,
    36558834998291,
    42087942047379,
    45619214182803,
    53216900345875,
    55906396437523,
)


def select(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the pinned 30 articles, ordered by ``(created_at, id)`` ascending.

    Raises :class:`ValueError` if any id in :data:`SELECTED_IDS` is absent from
    ``articles`` — a missing pinned article is a hard error, never a silent
    shortfall (the corpus must be exactly these 30).
    """
    by_id = {int(article["id"]): article for article in articles}
    missing = [article_id for article_id in SELECTED_IDS if article_id not in by_id]
    if missing:
        raise ValueError(
            f"selected article ids missing from the fetched corpus: {missing}"
        )
    return sorted(
        (by_id[article_id] for article_id in SELECTED_IDS),
        key=lambda article: (article["created_at"], int(article["id"])),
    )
