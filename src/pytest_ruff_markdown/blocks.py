"""Parses Markdown text into the Block objects pytest-ruff-markdown lints."""

from __future__ import annotations

import re
from pathlib import Path

# CommonMark allows a fence to be indented up to 3 spaces; its info string
# (everything after the marker) may not contain a backtick when the marker is
# made of backticks.
_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
_PYTHON_INFO = frozenset({"python", "py"})
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
        end_line: int,
        index: int,
        skip_reason: str | None = None,
        continues_from: CodeBlock | None = None,
    ) -> None:
        """Store a fenced block's source alongside its markdown position."""
        self.source = source
        # 1-indexed line, in the original markdown file, of the block's own
        # first line of content (not the ``` fence line).
        self.start_line = start_line
        # 1-indexed line of the block's own last line of content. Kept apart
        # from `source` because trailing blank lines are real lines that
        # `source.splitlines()` would not count. One less than `start_line`
        # for an empty block.
        self.end_line = end_line
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


def _closes_fence(line: str, marker: str) -> bool:
    """Whether line closes a fence opened with marker (CommonMark rules)."""
    stripped = line.rstrip()
    indent = len(stripped) - len(stripped.lstrip(" "))
    body = stripped.lstrip(" ")
    return (
        indent <= 3
        and len(body) >= len(marker)
        and body == body[0] * len(body)
        and body[0] == marker[0]
    )


def _find_fence_end(lines: list[str], content_start: int, marker: str) -> int:
    """Return the index of the line closing the fence, or len(lines) if none."""
    j = content_start
    while j < len(lines) and not _closes_fence(lines[j], marker):
        j += 1
    return j


def extract_python_blocks(
    markdown_text: str, *, source_name: str = "<markdown>"
) -> list[CodeBlock]:
    """Extract every ```python/```py fenced Block from markdown_text, in order."""
    lines = markdown_text.splitlines()
    blocks: list[CodeBlock] = []
    i = 0
    while i < len(lines):
        fence = _FENCE_RE.match(lines[i])
        if fence is None or (fence[2][0] == "`" and "`" in fence[3]):
            i += 1
            continue
        indent, marker, info = fence[1], fence[2], fence[3].strip()
        content_start = i + 1
        j = _find_fence_end(lines, content_start, marker)
        # Every fence is tracked so one nested in another is skipped along
        # with its parent, but only an unindented backtick python fence
        # yields a Block.
        if indent or marker[0] != "`" or info not in _PYTHON_INFO:
            i = j + 1
            continue
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
                end_line=j,
                index=len(blocks) + 1,
                skip_reason=skip_reason,
                continues_from=continues_from,
            )
        )
        i = j + 1
    return blocks


def synthetic_filename(block: CodeBlock, markdown_path: Path) -> Path:
    """Return block's Synthetic filename, resolved against markdown_path's dir."""
    return markdown_path.resolve().parent / (
        f"{markdown_path.stem}__block{block.index}.py"
    )
