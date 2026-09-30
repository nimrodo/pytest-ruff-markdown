"""Console-script entry point: reformats a markdown file's Blocks via `ruff format`."""

from __future__ import annotations

import argparse
import difflib
import os
import sys
from collections.abc import Iterable
from pathlib import Path

from .blocks import split_lines_keepends
from .formatting import BlockFormatError, format_markdown_text


def _is_skipped_dir(directory: Path) -> bool:
    """Whether a directory walk should not descend into directory."""
    return (
        directory.name.startswith(".")
        or directory.name == "node_modules"
        # A virtualenv, whatever it is called.
        or (directory / "pyvenv.cfg").exists()
    )


def _iter_markdown_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.is_dir():
            files.append(path)
            continue
        found: list[Path] = []
        for root, dirs, names in os.walk(path):
            dirs[:] = [d for d in dirs if not _is_skipped_dir(Path(root) / d)]
            found.extend(Path(root) / name for name in names if name.endswith(".md"))
        files.extend(sorted(found))
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
    for path in args.paths:
        if not path.exists():
            parser.error(f"no such file or directory: {path}")
    dry_run = args.check or args.diff

    any_changed = False
    any_error = False

    def report_error(error: BlockFormatError) -> None:
        nonlocal any_error
        any_error = True
        print(error, file=sys.stderr)

    for markdown_path in _iter_markdown_files(args.paths):
        # Bytes, not read_text/write_text: those translate line endings.
        original = markdown_path.read_bytes().decode("utf-8")
        new_text, changed = format_markdown_text(
            original, markdown_path, on_error=report_error
        )
        if not changed:
            continue
        any_changed = True
        if args.diff:
            sys.stdout.writelines(
                difflib.unified_diff(
                    split_lines_keepends(original),
                    split_lines_keepends(new_text),
                    fromfile=str(markdown_path),
                    tofile=str(markdown_path),
                )
            )
        if dry_run:
            print(f"Would reformat {markdown_path}")
        else:
            markdown_path.write_bytes(new_text.encode("utf-8"))
            print(f"Reformatted {markdown_path}")

    if any_error:
        return 2
    return 1 if (dry_run and any_changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
