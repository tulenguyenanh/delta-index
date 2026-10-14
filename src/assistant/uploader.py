"""Upload the cleaned corpus into a File Search store with per-document metadata.

Each Markdown file is streamed straight into the store via
``upload_to_file_search_store`` with ``source_url`` (plus ``article_id`` /
``title`` / ``updated_at`` / ``content_sha256``) attached as ``custom_metadata``
in the SAME call — metadata cannot be attached after the fact. The upload
``Operation`` is polled to completion with a bounded loop, and the returned
document name is kept so Phase 3 can delete-then-recreate a changed document.

``content_sha256`` is read verbatim off the ``CorpusDoc`` (computed once by
``read_corpus``); this module never re-reads the file and never imports from
``delta.py``, so the hash the store records is the same one the daily job
compares against on its next run.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from .corpus import CorpusDoc

# chars/4 approximates tokens. The File Search API exposes NO chunk count, so
# the reported number is a labelled estimate derived from the chunking_config
# sent with each upload — never presented as the server's own count.
_CHARS_PER_TOKEN = 4
_MAX_POLL_ITERATIONS = 30
_POLL_INTERVAL_SECONDS = 2.0


@dataclass
class UploadReport:
    """Result of one corpus upload: exact file count + a chunk estimate."""

    files: int
    est_chunks: int
    document_names: dict[str, str] = field(default_factory=dict)


def estimate_chunks(
    docs: list[CorpusDoc],
    max_tokens_per_chunk: int = 400,
    max_overlap_tokens: int = 40,
) -> int:
    """Estimate the total chunk count for ``docs`` under the chunking config sent.

    Pure function. The File Search API exposes **no** chunk count, so this is a
    documented estimate, never the server's own number: each document
    contributes ``max(1, ceil((chars // 4) / (max_tokens_per_chunk -
    max_overlap_tokens)))``, where ``chars // 4`` approximates its token count.
    """
    divisor = max(1, max_tokens_per_chunk - max_overlap_tokens)
    total = 0
    for doc in docs:
        text = doc.path.read_text(encoding="utf-8")
        tokens = len(text) // _CHARS_PER_TOKEN
        total += max(1, math.ceil(tokens / divisor))
    return total


def upload_corpus(
    client: genai.Client,
    store_name: str,
    docs: list[CorpusDoc],
    max_tokens_per_chunk: int = 400,
    max_overlap_tokens: int = 40,
) -> UploadReport:
    """Upload every doc sequentially; return counts and per-slug document names."""
    files = 0
    document_names: dict[str, str] = {}

    for doc in docs:
        operation = client.file_search_stores.upload_to_file_search_store(
            file_search_store_name=store_name,
            file=str(doc.path),
            config=types.UploadToFileSearchStoreConfig(
                display_name=doc.slug,
                mime_type="text/markdown",
                custom_metadata=[
                    types.CustomMetadata(key="source_url", string_value=doc.source_url),
                    types.CustomMetadata(
                        key="article_id", string_value=str(doc.article_id)
                    ),
                    types.CustomMetadata(key="title", string_value=doc.title),
                    types.CustomMetadata(key="updated_at", string_value=doc.updated_at),
                    types.CustomMetadata(
                        key="content_sha256", string_value=doc.content_sha256
                    ),
                ],
                chunking_config=types.ChunkingConfig(
                    white_space_config=types.WhiteSpaceConfig(
                        max_tokens_per_chunk=max_tokens_per_chunk,
                        max_overlap_tokens=max_overlap_tokens,
                    )
                ),
            ),
        )

        polls = 0
        while not operation.done:
            polls += 1
            if polls > _MAX_POLL_ITERATIONS:
                raise RuntimeError(
                    f"upload for {doc.slug} did not finish after "
                    f"{_MAX_POLL_ITERATIONS} polls"
                )
            time.sleep(_POLL_INTERVAL_SECONDS)
            operation = client.operations.get(operation)

        if operation.error:
            raise RuntimeError(f"upload failed for {doc.slug}: {operation.error}")

        files += 1
        document_names[doc.slug] = operation.response.document_name

    # One estimate, computed once from the same docs — the CLI reports this
    # exact number, so there is no second, divergent chunk computation.
    return UploadReport(
        files=files,
        est_chunks=estimate_chunks(docs, max_tokens_per_chunk, max_overlap_tokens),
        document_names=document_names,
    )
