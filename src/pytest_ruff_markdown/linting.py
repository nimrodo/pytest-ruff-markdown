"""Lints a single Block via a real `ruff` subprocess; one Block == one isolated file."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .blocks import CodeBlock


class RuffViolations(Exception):
    def __init__(self, violations: list[dict[str, Any]]) -> None:
        self.violations = violations


def lint_block(block: CodeBlock, markdown_path: Path) -> list[dict[str, Any]]:
    padded_source = "\n" * (block.start_line - 1) + block.source
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
    return json.loads(proc.stdout or "[]")
