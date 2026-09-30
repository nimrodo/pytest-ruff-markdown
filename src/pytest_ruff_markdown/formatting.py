"""Reformats a markdown file's Blocks via a real `ruff format` subprocess."""

from __future__ import annotations

import re
import uuid
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

# ruff reports a parse error as `Failed to parse <file>:<row>:<col>: <why>`.
_PARSE_ERROR_ROW_RE = re.compile(r"Failed to parse .*?(\d+):\d+: ")


class RuffFormatError(RuntimeError):
    """Raised when `ruff format` fails on a piece of source, e.g. a syntax error."""

    def __init__(self, message: str, line: int | None = None) -> None:
        """Keep the 1-indexed line of the source ruff blamed, when it named one."""
        super().__init__(message)
        self.line = line


class BlockFormatError(RuffFormatError):
    """Raised, or passed to `on_error`, when `ruff format` fails on a Block."""

    def __init__(self, block: CodeBlock, markdown_path: Path, detail: str) -> None:
        """Locate the failure at the Block's line in the markdown file."""
        super().__init__(f"{markdown_path}:{block.start_line}: {detail}")
        self.block = block


def format_block_source(source: str, stdin_filename: Path) -> str:
    """Run `ruff format -` on source, returning ruff's formatted output."""
    proc = run_ruff(["format", "-", "--stdin-filename", str(stdin_filename)], source)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        row = _PARSE_ERROR_ROW_RE.search(stderr)
        raise RuffFormatError(
            f"ruff format failed: {stderr}", int(row[1]) if row else None
        )
    return proc.stdout


def _line_ending(line: str) -> str:
    return "\r\n" if line.endswith("\r\n") else "\n"


def _chains(blocks: list[CodeBlock]) -> list[list[CodeBlock]]:
    """Group blocks into maximal `continues` chains; a lone Block is a chain."""
    chains: list[list[CodeBlock]] = []
    for block in blocks:
        if block.continues_from is None:
            chains.append([])
        chains[-1].append(block)
    return chains


def _block_at_row(chain: list[CodeBlock], row: int) -> CodeBlock:
    """Return the Block of chain that row of its joined source falls in."""
    owner, start = chain[0], 1
    for block in chain:
        if row < start:
            break
        owner = block
        # +1 for the sentinel line that follows every Block.
        start += len(block.source.split("\n")) + 1
    return owner


def _trim_blank_edges(lines: list[str]) -> list[str]:
    """Drop ruff's blank inter-Block spacing; it belongs to no Block."""
    start, end = 0, len(lines)
    while start < end and lines[start] == "":
        start += 1
    while end > start and lines[end - 1] == "":
        end -= 1
    return lines[start:end]


def _format_chain(chain: list[CodeBlock], markdown_path: Path) -> list[list[str]]:
    """Format chain as one file, returning each Block's new lines in order.

    Blocks are joined with a unique sentinel comment line so ruff sees each
    fragment in the context of the ones before it; the output is split on
    those lines again. Raises BlockFormatError, located at the Block to blame.
    """
    # Unique per call so no Block's own text can be mistaken for a boundary.
    sentinel = f"# pytest-ruff-markdown: block boundary {uuid.uuid4().hex}"
    joined = f"\n{sentinel}\n".join(block.source for block in chain)
    try:
        output = format_block_source(
            joined, synthetic_filename(chain[-1], markdown_path)
        )
    except RuffFormatError as exc:
        blamed = chain[0] if exc.line is None else _block_at_row(chain, exc.line)
        raise BlockFormatError(blamed, markdown_path, str(exc)) from exc

    parts: list[list[str]] = [[]]
    for line in split_lines(output):
        # ruff re-indents a comment to the code around it.
        if line.lstrip() == sentinel:
            parts.append([])
        else:
            parts[-1].append(line)
    if len(parts) != len(chain):
        # e.g. a Block ended inside a string, so ruff treated the sentinel
        # as text; there is no telling which lines are whose.
        first = next(block for block in chain if block.skip_reason is None)
        raise BlockFormatError(
            first,
            markdown_path,
            f"ruff changed the number of Block boundaries in a `continues` "
            f"chain from {len(chain) - 1} to {len(parts) - 1}",
        )
    return [_trim_blank_edges(part) for part in parts]


def _splice(lines: list[str], block: CodeBlock, formatted: list[str]) -> bool:
    """Replace block's lines with formatted in place; return whether they changed."""
    if formatted == block.lines:
        return False
    first, last = block.start_line - 1, block.end_line
    # New lines take the ending of the fence line above them; only an
    # unterminated Block at EOF may lack a final ending, and keeps lacking it.
    ending = _line_ending(lines[first - 1])
    new_lines = [line + ending for line in formatted]
    if new_lines and last > first and not lines[last - 1].endswith("\n"):
        new_lines[-1] = formatted[-1]
    lines[first:last] = new_lines
    return True


def format_markdown_text(
    markdown_text: str,
    markdown_path: Path,
    *,
    on_error: Callable[[BlockFormatError], None] | None = None,
) -> tuple[str, bool]:
    """Reformat every non-Skip-Marked Block in markdown_text.

    A chain of `continues` Blocks is formatted as one unit, each Block seeing
    the ones before it; a Skip-Marked Block in a chain is context only. Returns
    the new text (identical to markdown_text if nothing needed reformatting)
    and whether any Block actually changed. A Block, or chain, ruff cannot
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
    for chain in reversed(_chains(blocks)):
        if all(block.skip_reason is not None for block in chain):
            continue
        try:
            parts = _format_chain(chain, markdown_path)
        except BlockFormatError as error:
            # A Skip-Marked Block is the user's to keep as it is, so a failure
            # in it goes unreported; the chain it breaks is left untouched.
            if error.block.skip_reason is not None:
                continue
            if on_error is None:
                raise
            on_error(error)
            continue
        for block, formatted in reversed(list(zip(chain, parts, strict=True))):
            if block.skip_reason is None:
                changed |= _splice(lines, block, formatted)
    return "".join(lines), changed
