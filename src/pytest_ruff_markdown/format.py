"""Console-script entry point: reformats a markdown file's Blocks via `ruff format`."""

from __future__ import annotations

import argparse
import difflib
import sys
from collections.abc import Iterable
from pathlib import Path

from .formatting import format_markdown_text


def _iter_markdown_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
        else:
            files.append(path)
    return files


def main(argv: list[str] | None = None) -> int:
    """Reformat, or report on, the Blocks in the given markdown paths."""
    parser = argparse.ArgumentParser(prog="pytest-ruff-markdown-format")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit nonzero if any Block needs reformatting, without writing.",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Print a diff of the changes a Block needs, without writing.",
    )
    args = parser.parse_args(argv)
    dry_run = args.check or args.diff

    any_changed = False
    for markdown_path in _iter_markdown_files(args.paths):
        original = markdown_path.read_text(encoding="utf-8")
        new_text, changed = format_markdown_text(original, markdown_path)
        if not changed:
            continue
        any_changed = True
        if args.diff:
            sys.stdout.writelines(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile=str(markdown_path),
                    tofile=str(markdown_path),
                )
            )
        if dry_run:
            print(f"Would reformat {markdown_path}")
        else:
            markdown_path.write_text(new_text, encoding="utf-8")
            print(f"Reformatted {markdown_path}")

    return 1 if (dry_run and any_changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
