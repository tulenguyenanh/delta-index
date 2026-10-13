"""Trim residual chrome from Zendesk article HTML.

The API ``body`` field is already content-only, so this only drops the residual
junk the conversion step should not see: ``<script>``/``<style>`` elements,
HTML comments, and ``data-*`` tracking attributes. Pure function — no I/O, no
clock, so the output hash is stable.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Comment

_STRIP_TAGS = ("script", "style")


def clean_html(html: str) -> str:
    """Return ``html`` with scripts, styles, comments and ``data-*`` removed."""
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for element in soup.find_all(True):
        for attr in [name for name in element.attrs if name.startswith("data-")]:
            del element.attrs[attr]

    return str(soup)
