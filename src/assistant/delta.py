"""Three-way delta classification plus the delete-then-recreate applier.

``classify`` is pure: it compares each corpus document's fresh
``content_sha256`` (computed once by ``read_corpus``) against the hash the
store already holds for that slug, bucketing the corpus into added / updated /
skipped. No network call and no file-system read happens here — the store's
own per-document ``custom_metadata`` is the comparison source (the L1 rung),
with ``updated_at`` (L2) and a conservative "changed" default (L3) as
fallbacks for documents uploaded before the hash key existed.

``apply_delta`` is the only mutating part: for every changed slug it deletes
the existing document FIRST (``force=True``) and only then re-uploads, so the
store never transiently holds two copies of one slug. Nothing is wrapped in a
catch-and-continue — an exception propagates so the PaaS marks the run failed
and the log tells the truth.

Pure classifier, mutating applier; no clock, no logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from google import genai

from .corpus import CorpusDoc
from .store import delete_document
from .uploader import upload_corpus


def _metadata_map(document: Any) -> dict[str, str]:
    """Map ``document.custom_metadata`` to ``{key: string_value}``.

    Returns ``{}`` when the field is absent or ``None`` — a legacy document
    uploaded before the hash key existed — which sends classification down the
    L2/L3 ladder instead of raising.
    """
    metadata = getattr(document, "custom_metadata", None) or []
    return {entry.key: entry.string_value for entry in metadata}


@dataclass(frozen=True)
class DeltaCounts:
    """The DEPL-05 result: how many slugs each bucket held."""

    added: int
    updated: int
    skipped: int


@dataclass
class DeltaPlan:
    """The three buckets of work, resolved against the store's join key.

    ``updated`` pairs each changed corpus doc with the existing document's
    ``.name`` so the applier can delete the right document before re-uploading.
    """

    added: list[CorpusDoc] = field(default_factory=list)
    updated: list[tuple[CorpusDoc, str]] = field(default_factory=list)
    skipped: list[CorpusDoc] = field(default_factory=list)


def classify(docs: list[CorpusDoc], existing: dict[str, Any]) -> DeltaPlan:
    """Split ``docs`` into added / updated / skipped against ``existing``.

    Pure function: no network, no file-system call. The fresh hash arrives on
    each ``doc.content_sha256`` (populated by ``read_corpus``); this compares
    it against the store's stored metadata and never re-reads the file.

    For each doc in slug order:

    - slug absent from ``existing`` -> ``added``;
    - stored ``content_sha256`` present -> compare it (L1);
    - else stored ``updated_at`` present -> compare it (L2);
    - else -> treat as changed (L3, the safe default: re-upload, never skip).

    An equal comparison lands the doc in ``skipped``; a different one lands it
    in ``updated``, carrying the existing document's ``.name`` for the delete.
    """
    plan = DeltaPlan()
    for doc in sorted(docs, key=lambda item: item.slug):
        document = existing.get(doc.slug)
        if document is None:
            plan.added.append(doc)
            continue
        metadata = _metadata_map(document)
        stored_hash = metadata.get("content_sha256")
        if stored_hash is not None:
            changed = stored_hash != doc.content_sha256
        elif "updated_at" in metadata:
            changed = metadata["updated_at"] != doc.updated_at
        else:
            changed = True
        if changed:
            plan.updated.append((doc, document.name))
        else:
            plan.skipped.append(doc)
    return plan


def apply_delta(
    client: genai.Client, store_name: str, plan: DeltaPlan
) -> DeltaCounts:
    """Delete-then-recreate every updated slug, then upload the added ones.

    For each ``(doc, name)`` in ``plan.updated`` the existing document is
    deleted BEFORE its replacement is uploaded, so the store never holds two
    copies of one slug. Added docs are uploaded after. Exceptions are never
    swallowed — the caller's non-zero exit is what makes the PaaS mark the run
    failed.
    """
    for doc, document_name in plan.updated:
        delete_document(client, document_name)
        upload_corpus(client, store_name, [doc])
    upload_corpus(client, store_name, plan.added)
    return DeltaCounts(
        added=len(plan.added),
        updated=len(plan.updated),
        skipped=len(plan.skipped),
    )
