"""Pytest configuration: make the repository root importable from tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def gemini_client(monkeypatch):
    """A real ``genai.Client`` built from a dummy key.

    ``GOOGLE_API_KEY`` is set to a placeholder (never a real key) and ``respx``
    in each test intercepts the client's httpx transport, so no test needs or
    touches the live Gemini API.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from google import genai

    return genai.Client()
