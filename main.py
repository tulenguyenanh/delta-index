"""Run-once entrypoint for the OptiBot daily delta job.

Composes the whole path in one process::

    scrape -> read_corpus -> ensure_store -> list_store_documents
           -> classify -> apply_delta -> one counts line -> exit 0

The single printed ``added=N updated=N skipped=N deleted=N store_name=...``
line is the job's observable artifact (the GitHub Actions run log captures
stdout) and is derived from the real ``DeltaCounts``, never fabricated. Errors are not swallowed: a missing pinned
article prints a distinct ``FATAL:`` line and re-raises, so the platform marks
the run failed instead of recording a silent shortfall.

``API_KEY`` is aliased to ``GOOGLE_API_KEY`` (the name ``genai.Client()``
reads) before any SDK import, and only when ``GOOGLE_API_KEY`` is absent. The
alias shim is the only place that names the key, and its value is never
printed — the key crosses from the process environment into the SDK and
nowhere else.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

# Runs before the SDK import so genai.Client() sees the aliased key. Never
# prints the value; the alias is lazy so importing this module needs no key.
if "GOOGLE_API_KEY" not in os.environ and os.environ.get("API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["API_KEY"]

from src.assistant.config import STORE_DISPLAY_NAME  # noqa: E402
from src.assistant.corpus import read_corpus  # noqa: E402
from src.assistant.delta import apply_delta, classify  # noqa: E402
from src.assistant.store import (  # noqa: E402
    ensure_store,
    list_store_documents,
    make_client,
)
from src.scraper.pipeline import run as scrape  # noqa: E402

LAST_RUN_PATH = "last-run.json"


def main() -> int:
    """Scrape, classify the corpus against the store, apply the delta, exit 0."""
    try:
        scrape()
    except ValueError as exc:
        # A shortfall is a hard error (selection.select raises on a missing
        # pinned id). Name it distinctly, then re-raise — never a silent
        # 29-file run.
        print(f"FATAL: pinned article missing upstream: {exc}")
        raise

    docs = read_corpus()
    client = make_client()
    store_name = ensure_store(client, STORE_DISPLAY_NAME)
    existing = list_store_documents(client, store_name)
    plan = classify(docs, existing)
    counts = apply_delta(client, store_name, plan)

    print(
        f"added={counts.added} updated={counts.updated} "
        f"skipped={counts.skipped} deleted={counts.deleted} store_name={store_name}"
    )

    # A convenience artifact for local runs; in-container it dies with the
    # container, so the printed line above is the durable record.
    payload = json.dumps(
        {
            "added": counts.added,
            "updated": counts.updated,
            "skipped": counts.skipped,
            "deleted": counts.deleted,
            "store_name": store_name,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
    ) + "\n"
    with open(LAST_RUN_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
