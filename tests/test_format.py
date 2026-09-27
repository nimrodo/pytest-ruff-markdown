"""Core reformatting logic (`format_markdown_text`) plus the
`pytest-ruff-markdown-format` CLI (`format.main`): rewrites, or with
`--check`/`--diff` reports on, every non-Skip-Marked Block's `ruff format`
output in place, preserving the rest of the markdown file byte-for-byte.
"""

from pathlib import Path

from pytest_ruff_markdown.format import main
from pytest_ruff_markdown.formatting import format_markdown_text


def test_unformatted_block_is_reformatted():
    markdown_text = "# Doc\n\n```python\nx=1\n```\n"

    new_text, changed = format_markdown_text(markdown_text, Path("example.md"))

    assert changed
    assert new_text == "# Doc\n\n```python\nx = 1\n```\n"


def test_already_formatted_block_is_unchanged():
    markdown_text = "# Doc\n\n```python\nx = 1\n```\n"

    new_text, changed = format_markdown_text(markdown_text, Path("example.md"))

    assert not changed
    assert new_text == markdown_text


def test_skip_marked_block_is_not_reformatted():
    markdown_text = (
        "# Doc\n\n<!-- pytest-ruff-markdown: skip -->\n```python\nx=1\n```\n"
    )

    new_text, changed = format_markdown_text(markdown_text, Path("example.md"))

    assert not changed
    assert new_text == markdown_text


def test_crlf_file_keeps_crlf_line_endings():
    markdown_text = "# Doc\r\n\r\n```python\r\nx=1\r\n```\r\n"

    new_text, changed = format_markdown_text(markdown_text, Path("example.md"))

    assert changed
    assert new_text == "# Doc\r\n\r\n```python\r\nx = 1\r\n```\r\n"


def test_only_the_unformatted_block_changes_others_are_preserved():
    markdown_text = (
        "# Doc\n\n"
        "```python\n"
        "x = 1\n"
        "```\n\n"
        "Some prose in between.\n\n"
        "```python\n"
        "y=2\n"
        "```\n"
    )

    new_text, changed = format_markdown_text(markdown_text, Path("example.md"))

    assert changed
    assert new_text == (
        "# Doc\n\n"
        "```python\n"
        "x = 1\n"
        "```\n\n"
        "Some prose in between.\n\n"
        "```python\n"
        "y = 2\n"
        "```\n"
    )


def test_cli_rewrites_file_in_place(tmp_path):
    md = tmp_path / "example.md"
    md.write_text("# Doc\n\n```python\nx=1\n```\n", encoding="utf-8")

    exit_code = main([str(md)])

    assert exit_code == 0
    assert md.read_text(encoding="utf-8") == "# Doc\n\n```python\nx = 1\n```\n"


def test_cli_check_mode_does_not_write_and_exits_nonzero(tmp_path):
    md = tmp_path / "example.md"
    original = "# Doc\n\n```python\nx=1\n```\n"
    md.write_text(original, encoding="utf-8")

    exit_code = main([str(md), "--check"])

    assert exit_code == 1
    assert md.read_text(encoding="utf-8") == original


def test_cli_exits_zero_when_nothing_needs_reformatting(tmp_path):
    md = tmp_path / "example.md"
    md.write_text("# Doc\n\n```python\nx = 1\n```\n", encoding="utf-8")

    exit_code = main([str(md), "--check"])

    assert exit_code == 0


def test_cli_walks_directories_for_markdown_files(tmp_path):
    nested = tmp_path / "docs"
    nested.mkdir()
    md = nested / "example.md"
    md.write_text("# Doc\n\n```python\nx=1\n```\n", encoding="utf-8")

    exit_code = main([str(tmp_path)])

    assert exit_code == 0
    assert md.read_text(encoding="utf-8") == "# Doc\n\n```python\nx = 1\n```\n"


def test_cli_diff_mode_prints_a_diff_without_writing(tmp_path, capsys):
    md = tmp_path / "example.md"
    original = "# Doc\n\n```python\nx=1\n```\n"
    md.write_text(original, encoding="utf-8")

    exit_code = main([str(md), "--diff"])

    assert exit_code == 1
    assert md.read_text(encoding="utf-8") == original
    captured = capsys.readouterr()
    assert "-x=1" in captured.out
    assert "+x = 1" in captured.out
