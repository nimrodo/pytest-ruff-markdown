"""Lints a single Block via a real `ruff` subprocess; one Block == one isolated file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._ruff import run_ruff
from .blocks import CodeBlock, synthetic_filename


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
    buffer = [""] * last.end_line
    for member in chain:
        for offset, line in enumerate(member.lines):
            buffer[member.start_line - 1 + offset] = line
    # A real file ends with a newline; without one ruff flags W292 on every
    # Block. An empty Block stays an empty file.
    return "\n".join(buffer) + "\n" if buffer else ""


def lint_block(block: CodeBlock, markdown_path: Path) -> list[dict[str, Any]]:
    """Run `ruff check` on block plus any `continues` context.

    Returns only the violations attributable to block's own lines.
    """
    chain = _chain(block)
    padded_source = _padded_chain_source(chain)

    proc = run_ruff(
        [
            "check",
            "-",
            "--stdin-filename",
            str(synthetic_filename(block, markdown_path)),
            "--output-format=json",
            # A project's `fix = true` would make ruff print its fix summary
            # after the JSON, which then no longer parses.
            "--no-fix",
            # D100 (missing module docstring) is a category error against a
            # Block: a fenced snippet structurally cannot have a module
            # docstring, so this fires unconditionally regardless of the
            # user's own `select` config.
            "--extend-ignore",
            "D100",
        ],
        padded_source,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"ruff failed unexpectedly: {proc.stderr}")
    violations: list[dict[str, Any]] = json.loads(proc.stdout or "[]")

    return [
        violation
        for violation in violations
        if block.start_line
        <= (violation.get("location") or {}).get("row", -1)
        <= block.end_line
    ]
