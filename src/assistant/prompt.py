"""The verbatim OptiBot system prompt — the single source of truth.

Pure module — no I/O, no clock, no network.
"""

from __future__ import annotations

# Source: "OptiSigns – Take-Home Test (Coding + Planning).docx.md" lines 56-66.
OPTIBOT_SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
- Tone: helpful, factual, concise.
- Only answer using the uploaded docs.
- Max 5 bullet points; else link to the doc.
- Cite up to 3 "Article URL:" lines per reply."""
