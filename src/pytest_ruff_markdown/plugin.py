"""pytest11 collection: turns each Block in a .md file into a linted pytest item."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from .blocks import CodeBlock, extract_python_blocks
from .linting import RuffViolations, lint_block

if TYPE_CHECKING:
    # Not part of pytest's public API, but there's no public alias for it;
    # only used here (under TYPE_CHECKING) to match Node.repr_failure's
    # exact signature so overriding it doesn't violate Liskov substitution.
    from _pytest._code.code import TracebackStyle


def pytest_collect_file(
    file_path: Path, parent: pytest.Collector
) -> pytest.Collector | None:
    """Collect file_path as a MarkdownFile if it's a .md file, else skip it."""
    if file_path.suffix == ".md":
        return MarkdownFile.from_parent(parent, path=file_path)
    return None


class MarkdownFile(pytest.File):
    """A collected .md file, yielding one MarkdownCodeBlockItem per Block."""

    def collect(self) -> Any:
        """Yield a MarkdownCodeBlockItem for every Block in this file."""
        text = self.path.read_text(encoding="utf-8")
        for block in extract_python_blocks(text):
            yield MarkdownCodeBlockItem.from_parent(
                self,
                name=f"L{block.start_line}",
                block=block,
            )


class MarkdownCodeBlockItem(pytest.Item):
    """A single Block, linted and reported as its own pytest item."""

    def __init__(self, *, block: CodeBlock, **kwargs: Any) -> None:
        """Attach the Block this item lints."""
        super().__init__(**kwargs)
        self.block = block

    def runtest(self) -> None:
        """Lint the Block, skipping it if marked, failing on any violation."""
        if self.block.skip_reason is not None:
            pytest.skip(self.block.skip_reason)
        violations = lint_block(self.block, self.path)
        if violations:
            raise RuffViolations(violations)

    def repr_failure(
        self,
        excinfo: pytest.ExceptionInfo[BaseException],
        style: TracebackStyle | None = None,
    ) -> str:
        """Render each ruff violation as one `path:row: code message` line."""
        if isinstance(excinfo.value, RuffViolations):
            lines = []
            for violation in excinfo.value.violations:
                location = violation.get("location") or {}
                row = location.get("row", "?")
                code = violation.get("code", "?")
                message = violation.get("message", "")
                lines.append(f"{self.path}:{row}: {code} {message}")
            return "\n".join(lines)
        return str(super().repr_failure(excinfo, style))

    def reportinfo(self) -> tuple[Path, int, str]:
        """Report this item's location as the Block's own line in the markdown file."""
        return self.path, self.block.start_line - 1, f"L{self.block.start_line}"
