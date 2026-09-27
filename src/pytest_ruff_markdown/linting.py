"""Lints a single Block via a real `ruff` subprocess; one Block == one isolated file."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .blocks import CodeBlock


class RuffViolations(Exception):
    """Raised by a pytest item when `ruff` reports violations for its Block."""

    def __init__(self, violations: list[dict[str, Any]]) -> None:
        """Store the raw `ruff --output-format=json` violation records."""
        self.violations = violations


def _chain(block: CodeBlock) -> list[CodeBlock]:
    """Return block's `continues` chain, from its root ancestor to itself."""
    chain: list[CodeBlock] = []
    current: CodeBlock | None = block
    while current is not None:
        chain.append(current)
        current = current.continues_from
    chain.reverse()
    return chain


def _padded_chain_source(chain: list[CodeBlock]) -> str:
    """Concatenate chain's Blocks at their real markdown line positions."""
    last = chain[-1]
    total_lines = max(last.start_line + len(last.source.splitlines()) - 1, 0)
    buffer = [""] * total_lines
    for member in chain:
        for offset, line in enumerate(member.source.splitlines()):
            buffer[member.start_line - 1 + offset] = line
    return "\n".join(buffer)


def lint_block(block: CodeBlock, markdown_path: Path) -> list[dict[str, Any]]:
    """Run `ruff check` on block plus any `continues` context.

    Returns only the violations attributable to block's own lines.
    """
    chain = _chain(block)
    padded_source = _padded_chain_source(chain)
    stdin_filename = markdown_path.resolve().parent / (
        f"{markdown_path.stem}__block{block.index}.py"
    )

    proc = subprocess.run(
        [
            "ruff",
            "check",
            "-",
            "--stdin-filename",
            str(stdin_filename),
            "--output-format=json",
            # D100 (missing module docstring) is a category error against a
            # Block: a fenced snippet structurally cannot have a module
            # docstring, so this fires unconditionally regardless of the
            # user's own `select` config.
            "--extend-ignore",
            "D100",
        ],
        input=padded_source,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"ruff failed unexpectedly: {proc.stderr}")
    violations: list[dict[str, Any]] = json.loads(proc.stdout or "[]")

    block_start = block.start_line
    block_end = block_start + len(block.source.splitlines()) - 1
    return [
        violation
        for violation in violations
        if block_start <= (violation.get("location") or {}).get("row", -1) <= block_end
    ]
