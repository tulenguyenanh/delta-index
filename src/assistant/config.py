"""Runtime configuration for the assistant. Reads env only; holds no keys.

``load_dotenv()`` is for local development only — in the deployed image the
platform injects the environment. The API key is never read here: only
``genai.Client()`` (in ``store.py``) touches ``GOOGLE_API_KEY``, so nothing in
this module can echo it.

Pure module — no I/O beyond the one-time ``.env`` read, no clock, no network.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # local dev only; production injects env vars

# Supported File Search model ids churn; keep the default overridable.
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-3.8-flash"

# Full "fileSearchStores/<id>" override. When set it takes precedence over the
# display-name lookup in ensure_store (display names are not a unique key).
GEMINI_STORE_NAME = os.getenv("GEMINI_STORE_NAME") or None

# The reuse key for ensure_store: a re-run matches this display name instead of
# creating a second store.
STORE_DISPLAY_NAME = (
    os.getenv("GEMINI_STORE_DISPLAY_NAME") or "optibot-knowledge-base"
)
