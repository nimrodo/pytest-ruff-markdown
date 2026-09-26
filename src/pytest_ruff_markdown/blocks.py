"""Parses Markdown text into the Block objects pytest-ruff-markdown lints."""

from __future__ import annotations

import re

_FENCE_START_RE = re.compile(r"^```(?:python|py)\s*$")
_FENCE_END_RE = re.compile(r"^```\s*$")
_SKIP_MARKER_RE = re.compile(r"^<!--\s*pytest-ruff-markdown:\s*skip\s*-->\s*$")
_SKIP_REASON = "excluded via `pytest-ruff-markdown: skip`"


class CodeBlock:
    """A ```python/```py fenced block extracted from a markdown file."""

    def __init__(
        self,
        source: str,
        start_line: int,
        index: int,
        skip_reason: str | None = None,
    ) -> None:
        """Store a fenced block's source alongside its markdown position."""
        self.source = source
        # 1-indexed line, in the original markdown file, of the block's own
        # first line of content (not the ``` fence line).
        self.start_line = start_line
        # 1-indexed position among the *collected* blocks in this file, used
        # only to build a stable, per-block synthetic ruff filename.
        self.index = index
        # Set when the fence was immediately preceded by the
        # `<!-- pytest-ruff-markdown: skip -->` marker; the block is then
        # never passed to ruff.
        self.skip_reason = skip_reason


def extract_python_blocks(markdown_text: str) -> list[CodeBlock]:
    """Extract every ```python/```py fenced Block from markdown_text, in order."""
    lines = markdown_text.splitlines()
    blocks: list[CodeBlock] = []
    i = 0
    while i < len(lines):
        if _FENCE_START_RE.match(lines[i]):
            content_start = i + 1
            j = content_start
            while j < len(lines) and not _FENCE_END_RE.match(lines[j]):
                j += 1
            skip_reason = (
                _SKIP_REASON if i > 0 and _SKIP_MARKER_RE.match(lines[i - 1]) else None
            )
            blocks.append(
                CodeBlock(
                    source="\n".join(lines[content_start:j]),
                    start_line=content_start + 1,
                    index=len(blocks) + 1,
                    skip_reason=skip_reason,
                )
            )
            i = j + 1
        else:
            i += 1
    return blocks
