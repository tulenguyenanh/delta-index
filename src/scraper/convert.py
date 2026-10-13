"""HTML -> Markdown conversion with an iframe converter.

``markdownify`` has no default handling for ``<iframe>``: an embed whose only
content is a ``src`` is silently dropped. ``OptiMarkdown`` restores it as a
Markdown link. Pure function — no I/O, no clock.
"""

from __future__ import annotations

from markdownify import MarkdownConverter


class OptiMarkdown(MarkdownConverter):
    """Markdownify subclass that preserves iframe embeds as links."""

    def convert_iframe(self, el, text, parent_tags):
        src = el.get("src") or ""
        return f"\n\n[Embedded video]({src})\n\n" if src else ""


def to_markdown(html: str) -> str:
    """Convert ``html`` to deterministic Markdown (ATX headings, no wrapping)."""
    return (
        OptiMarkdown(
            heading_style="ATX",
            keep_inline_images_in=["td", "th"],
            wrap=False,
        )
        .convert(html)
        .strip()
        + "\n"
    )
