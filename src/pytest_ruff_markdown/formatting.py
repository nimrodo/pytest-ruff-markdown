"""Reformats a markdown file's Blocks via a real `ruff format` subprocess."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ._ruff import run_ruff
from .blocks import (
    CodeBlock,
    extract_python_blocks,
    split_lines,
    split_lines_keepends,
    synthetic_filename,
)


class RuffFormatError(RuntimeError):
    """Raised when `ruff format` fails on a piece of source, e.g. a syntax error."""


class BlockFormatError(RuffFormatError):
    """Raised, or passed to `on_error`, when `ruff format` fails on a Block."""

    def __init__(self, block: CodeBlock, markdown_path: Path, detail: str) -> None:
        """Locate the failure at the Block's line in the markdown file."""
        super().__init__(f"{markdown_path}:{block.start_line}: {detail}")


def format_block_source(source: str, stdin_filename: Path) -> str:
    """Run `ruff format -` on source, returning ruff's formatted output."""
    proc = run_ruff(["format", "-", "--stdin-filename", str(stdin_filename)], source)
    if proc.returncode != 0:
        raise RuffFormatError(f"ruff format failed: {proc.stderr.strip()}")
    return proc.stdout


def _line_ending(line: str) -> str:
    return "\r\n" if line.endswith("\r\n") else "\n"


def format_markdown_text(
    markdown_text: str,
    markdown_path: Path,
    *,
    on_error: Callable[[BlockFormatError], None] | None = None,
) -> tuple[str, bool]:
    """Reformat every non-Skip-Marked Block in markdown_text.

    Returns the new text (identical to markdown_text if nothing needed
    reformatting) and whether any Block actually changed. A Block ruff cannot
    format (e.g. a syntax error) is left as it is and passed to `on_error`;
    without an `on_error` it is raised instead.
    """
    blocks = extract_python_blocks(markdown_text, source_name=str(markdown_path))
    # Each line keeps its own ending, so the rebuilt text stays byte-for-byte
    # faithful outside changed Blocks, including on a CRLF or mixed file.
    lines = split_lines_keepends(markdown_text)
    changed = False
    # Splice from the bottom up: a Block whose formatted output has a
    # different line count shifts every line index after it, but never one
    # before it, so later Blocks must be spliced first.
    for block in reversed(blocks):
        if block.skip_reason is not None:
            continue
        try:
            formatted = split_lines(
                format_block_source(
                    block.source, synthetic_filename(block, markdown_path)
                )
            )
        except RuffFormatError as exc:
            error = BlockFormatError(block, markdown_path, str(exc))
            if on_error is None:
                raise error from exc
            on_error(error)
            continue
        if formatted == block.lines:
            continue
        changed = True
        first, last = block.start_line - 1, block.end_line
        # New lines take the ending of the fence line above them; only an
        # unterminated Block at EOF may lack a final ending, and keeps lacking it.
        ending = _line_ending(lines[first - 1])
        new_lines = [line + ending for line in formatted]
        if new_lines and last > first and not lines[last - 1].endswith("\n"):
            new_lines[-1] = formatted[-1]
        lines[first:last] = new_lines
    return "".join(lines), changed
