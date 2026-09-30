"""Line-ending fidelity: only `\\n` and `\\r\\n` end a line. Every other
character `str.splitlines()` would split on (form feed, NEL, U+2028, ...) is
ordinary text, and the formatter leaves everything outside a changed Block
byte-for-byte alone, including each line's own ending.
"""

from pathlib import Path

import pytest

from pytest_ruff_markdown.blocks import extract_python_blocks
from pytest_ruff_markdown.format import main
from pytest_ruff_markdown.formatting import format_markdown_text

EXOTIC_SEPARATORS = ["\x0b", "\x0c", "\x1c", "\x85", " ", " "]


@pytest.mark.parametrize("separator", EXOTIC_SEPARATORS)
def test_exotic_separator_in_prose_does_not_shift_block_line_numbers(separator):
    markdown_text = f"a{separator}b\n\n```python\nx=1\n```\n"

    (block,) = extract_python_blocks(markdown_text)

    assert block.start_line == 4


@pytest.mark.parametrize("separator", EXOTIC_SEPARATORS)
def test_exotic_separator_in_prose_survives_reformatting(separator):
    markdown_text = f"a{separator}b\n\n```python\nx=1\n```\n"

    new_text, changed = format_markdown_text(markdown_text, Path("example.md"))

    assert changed
    assert new_text == f"a{separator}b\n\n```python\nx = 1\n```\n"


def test_cli_preserves_crlf_line_endings(tmp_path):
    md = tmp_path / "example.md"
    md.write_bytes(b"# Doc\r\n\r\n```python\r\nx=1\r\ny=2\r\n```\r\n")

    assert main([str(md)]) == 0

    assert md.read_bytes() == b"# Doc\r\n\r\n```python\r\nx = 1\r\ny = 2\r\n```\r\n"


def test_reformatting_keeps_each_lines_own_ending_in_a_mixed_file():
    markdown_text = "lf line\n\r\n```python\r\nx=1\r\n```\nlast\r\n"

    new_text, changed = format_markdown_text(markdown_text, Path("example.md"))

    assert changed
    assert new_text == "lf line\n\r\n```python\r\nx = 1\r\n```\nlast\r\n"


def test_reformatting_keeps_a_missing_final_newline():
    markdown_text = "```python\nx=1\n```"

    new_text, _ = format_markdown_text(markdown_text, Path("example.md"))

    assert new_text == "```python\nx = 1\n```"


def test_reformatting_an_unterminated_block_at_eof_without_newline():
    markdown_text = "```python\nx=1"

    new_text, changed = format_markdown_text(markdown_text, Path("example.md"))

    assert changed
    assert new_text == "```python\nx = 1"


def test_trailing_blank_lines_in_a_block_are_formatted_away():
    markdown_text = "```python\nx = 1\n\n\n```\n"

    new_text, changed = format_markdown_text(markdown_text, Path("example.md"))

    assert changed
    assert new_text == "```python\nx = 1\n```\n"
