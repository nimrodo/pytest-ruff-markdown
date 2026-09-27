"""Parses Markdown text into the Block objects pytest-ruff-markdown lints."""

from __future__ import annotations

import re

_FENCE_START_RE = re.compile(r"^```(?:python|py)\s*$")
_FENCE_END_RE = re.compile(r"^```\s*$")
_SKIP_MARKER_RE = re.compile(r"^<!--\s*pytest-ruff-markdown:\s*skip\s*-->\s*$")
_CONTINUES_MARKER_RE = re.compile(
    r"^<!--\s*pytest-ruff-markdown:\s*continues\s*-->\s*$"
)
_SKIP_REASON = "excluded via `pytest-ruff-markdown: skip`"


class ContinuesMarkerError(Exception):
    """Raised when `pytest-ruff-markdown: continues` marks a file's first Block."""


class CodeBlock:
    """A ```python/```py fenced block extracted from a markdown file."""

    def __init__(
        self,
        source: str,
        start_line: int,
        index: int,
        skip_reason: str | None = None,
        continues_from: CodeBlock | None = None,
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
        # Set to the immediately preceding Block when the fence was
        # immediately preceded by the `<!-- pytest-ruff-markdown: continues
        # -->` marker. That Block may itself have a `continues_from`,
        # forming a chain; linting walks it to build up context.
        self.continues_from = continues_from


def extract_python_blocks(
    markdown_text: str, *, source_name: str = "<markdown>"
) -> list[CodeBlock]:
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
            marker_line = lines[i - 1] if i > 0 else ""
            skip_reason = _SKIP_REASON if _SKIP_MARKER_RE.match(marker_line) else None
            continues_from: CodeBlock | None = None
            if _CONTINUES_MARKER_RE.match(marker_line):
                if not blocks:
                    raise ContinuesMarkerError(
                        f"{source_name}: Block at line {content_start + 1} is "
                        "marked `pytest-ruff-markdown: continues` but is the "
                        "first Block in the file -- there is no preceding "
                        "Block to continue from"
                    )
                continues_from = blocks[-1]
            blocks.append(
                CodeBlock(
                    source="\n".join(lines[content_start:j]),
                    start_line=content_start + 1,
                    index=len(blocks) + 1,
                    skip_reason=skip_reason,
                    continues_from=continues_from,
                )
            )
            i = j + 1
        else:
            i += 1
    return blocks
