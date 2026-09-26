"""pytest11 collection: turns each Block in a collected .md file into a linted pytest item."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from .blocks import CodeBlock, extract_python_blocks
from .linting import RuffViolations, lint_block


def pytest_collect_file(
    file_path: Path, parent: pytest.Collector
) -> pytest.Collector | None:
    if file_path.suffix == ".md":
        return MarkdownFile.from_parent(parent, path=file_path)
    return None


class MarkdownFile(pytest.File):
    def collect(self) -> Any:
        text = self.path.read_text(encoding="utf-8")
        for block in extract_python_blocks(text):
            yield MarkdownCodeBlockItem.from_parent(
                self,
                name=f"L{block.start_line}",
                block=block,
            )


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
