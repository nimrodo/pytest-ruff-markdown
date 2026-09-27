"""Reformats a markdown file's Blocks via a real `ruff format` subprocess."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .blocks import extract_python_blocks, synthetic_filename


def format_block_source(source: str, stdin_filename: Path) -> str:
    """Run `ruff format -` on source, returning ruff's formatted output."""
    proc = subprocess.run(
        ["ruff", "format", "-", "--stdin-filename", str(stdin_filename)],
        input=source,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ruff format failed unexpectedly: {proc.stderr}")
    return proc.stdout


def format_markdown_text(markdown_text: str, markdown_path: Path) -> tuple[str, bool]:
    """Reformat every non-Skip-Marked Block in markdown_text.

    Returns the new text (identical to markdown_text if nothing needed
    reformatting) and whether any Block actually changed.
    """
    blocks = extract_python_blocks(markdown_text, source_name=str(markdown_path))
    lines = markdown_text.splitlines()
    # str.splitlines() discards the original line-ending style; remember it
    # so the rebuilt text stays byte-for-byte faithful outside changed
    # Blocks, including on a CRLF file.
    newline = "\r\n" if "\r\n" in markdown_text else "\n"
    changed = False
    # Splice from the bottom up: a Block whose formatted output has a
    # different line count shifts every line index after it, but never one
    # before it, so later Blocks must be spliced first.
    for block in reversed(blocks):
        if block.skip_reason is not None:
            continue
        original_lines = block.source.splitlines()
        formatted_lines = format_block_source(
            block.source, synthetic_filename(block, markdown_path)
        ).splitlines()
        if formatted_lines == original_lines:
            continue
        changed = True
        start = block.start_line - 1
        lines[start : start + len(original_lines)] = formatted_lines
    new_text = newline.join(lines)
    if markdown_text.endswith("\n"):
        new_text += newline
    return new_text, changed
