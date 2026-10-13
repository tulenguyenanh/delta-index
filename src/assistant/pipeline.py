"""Orchestrator and CLI entrypoint for the corpus upload.

Wires the whole path together: read_corpus -> make_client -> ensure_store ->
upload_corpus -> report. This is the Phase 3 ``main.py`` will call.

Usage::

    python -m src.assistant.pipeline
"""

from __future__ import annotations

import argparse

from google import genai

from .config import STORE_DISPLAY_NAME
from .corpus import read_corpus
from .store import ensure_store, make_client
from .uploader import UploadReport, upload_corpus


def run(client: genai.Client | None = None) -> UploadReport:
    """Upload the corpus and print the exact file count + chunk estimate."""
    docs = read_corpus()
    resolved = make_client(client)
    store_name = ensure_store(resolved, STORE_DISPLAY_NAME)
    report = upload_corpus(resolved, store_name, docs)

    print(f"files_embedded={len(report.document_names)}")
    print(f"chunks_embedded_estimate={report.est_chunks}")
    print(f"store_name={store_name}")
    for slug, document_name in report.document_names.items():
        print(f"{slug} -> {document_name}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upload the cleaned Markdown corpus to a Gemini File Search store."
    )
    parser.parse_args(argv)
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
