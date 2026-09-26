"""pytest-ruff-markdown: lints Python code fences in Markdown files via ruff.

This module is registered as a pytest11 entry point (see pyproject.toml),
which is what makes it discoverable as an installed pytest plugin.

Every ```python/```py fenced block in a collected .md file becomes its own
pytest item, linted by piping the block through a real `ruff` subprocess.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

_FENCE_START_RE = re.compile(r"^```(?:python|py)\s*$")
_FENCE_END_RE = re.compile(r"^```\s*$")
_SKIP_MARKER_RE = re.compile(r"^<!--\s*pytest-ruff-markdown:\s*skip\s*-->\s*$")
_SKIP_REASON = "excluded via `pytest-ruff-markdown: skip`"


def pytest_collect_file(
    file_path: Path, parent: pytest.Collector
) -> pytest.Collector | None:
    if file_path.suffix == ".md":
        return MarkdownFile.from_parent(parent, path=file_path)
    return None


class CodeBlock:
    """A ```python/```py fenced block extracted from a markdown file."""

    def __init__(
        self,
        source: str,
        start_line: int,
        index: int,
        skip_reason: str | None = None,
    ) -> None:
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
        ],
        input=padded_source,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"ruff failed unexpectedly: {proc.stderr}")
    return json.loads(proc.stdout or "[]")


class MarkdownFile(pytest.File):
    def collect(self) -> Any:
        text = self.path.read_text(encoding="utf-8")
        for block in extract_python_blocks(text):
            yield MarkdownCodeBlockItem.from_parent(
                self,
                name=f"L{block.start_line}",
                block=block,
            )


class RuffViolations(Exception):
    def __init__(self, violations: list[dict[str, Any]]) -> None:
        self.violations = violations


class MarkdownCodeBlockItem(pytest.Item):
    def __init__(self, *, block: CodeBlock, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.block = block

    def runtest(self) -> None:
        if self.block.skip_reason is not None:
            pytest.skip(self.block.skip_reason)
        violations = lint_block(self.block, self.path)
        if violations:
            raise RuffViolations(violations)

    def repr_failure(self, excinfo: pytest.ExceptionInfo[BaseException]) -> str:
        if isinstance(excinfo.value, RuffViolations):
            lines = []
            for violation in excinfo.value.violations:
                location = violation.get("location") or {}
                row = location.get("row", "?")
                code = violation.get("code", "?")
                message = violation.get("message", "")
                lines.append(f"{self.path}:{row}: {code} {message}")
            return "\n".join(lines)
        return str(super().repr_failure(excinfo))

    def reportinfo(self) -> tuple[Path, int, str]:
        return self.path, self.block.start_line - 1, f"L{self.block.start_line}"
