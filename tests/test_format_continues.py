"""A `continues` chain is formatted as one unit, so a Block that is only valid
in the context of its predecessors (e.g. an indented method body) formats
cleanly, as linting already lets it lint.
"""

import subprocess
from pathlib import Path

import pytest

from pytest_ruff_markdown import formatting
from pytest_ruff_markdown.format import main
from pytest_ruff_markdown.formatting import BlockFormatError, format_markdown_text

CONTINUES = "<!-- pytest-ruff-markdown: continues -->\n"
SKIP = "<!-- pytest-ruff-markdown: skip -->\n"


def _format(text: str, **kwargs):
    return format_markdown_text(text, Path("example.md"), **kwargs)


def test_fragment_valid_only_in_context_formats_without_error():
    markdown_text = (
        "```python\nclass A:\n    x = 1\n```\n\n"
        + CONTINUES
        + "```python\n    def f(self):\n        return 1\n```\n"
    )
    errors: list[BlockFormatError] = []

    new_text, changed = _format(markdown_text, on_error=errors.append)

    assert errors == []
    assert not changed
    assert new_text == markdown_text


def test_each_blocks_own_lines_in_a_chain_are_rewritten():
    markdown_text = (
        "Intro.\n\n"
        "```python\nclass A:\n    x=1\n```\n\n"
        "Between.\n\n"
        + CONTINUES
        + "```python\n    def f(self):\n      return  1\n```\n"
    )

    new_text, changed = _format(markdown_text)

    assert changed
    assert new_text == (
        "Intro.\n\n"
        "```python\nclass A:\n    x = 1\n```\n\n"
        "Between.\n\n"
        + CONTINUES
        + "```python\n    def f(self):\n        return 1\n```\n"
    )


def test_chain_formatting_keeps_crlf_endings():
    markdown_text = (
        "```python\r\nclass A:\r\n    x=1\r\n```\r\n"
        + CONTINUES.replace("\n", "\r\n")
        + "```python\r\n    def f(self):\r\n      return  1\r\n```\r\n"
    )

    new_text, _ = _format(markdown_text)

    assert new_text == (
        "```python\r\nclass A:\r\n    x = 1\r\n```\r\n"
        + CONTINUES.replace("\n", "\r\n")
        + "```python\r\n    def f(self):\r\n        return 1\r\n```\r\n"
    )


def test_chain_formatting_is_idempotent():
    markdown_text = (
        "```python\nclass A:\n    x=1\n```\n"
        + CONTINUES
        + "```python\n    def f(self):\n      return  1\n```\n"
    )

    once, _ = _format(markdown_text)
    twice, changed = _format(once)

    assert not changed
    assert twice == once


def test_three_block_chain_is_formatted_as_one_unit():
    markdown_text = (
        "```python\nimport os\n```\n"
        + CONTINUES
        + "```python\nclass A:\n    x=os.sep\n```\n"
        + CONTINUES
        + "```python\n    def f(self):\n      return  1\n```\n"
    )

    new_text, _ = _format(markdown_text)

    assert new_text == (
        "```python\nimport os\n```\n"
        + CONTINUES
        + "```python\nclass A:\n    x = os.sep\n```\n"
        + CONTINUES
        + "```python\n    def f(self):\n        return 1\n```\n"
    )


def test_syntax_error_in_chain_is_reported_once_at_the_offending_block():
    markdown_text = (
        "```python\nclass A:\n    x=1\n```\n\n"  # lines 2-4
        + CONTINUES  # line 6
        + "```python\n    def f(self) return 1\n```\n"  # content at line 8
    )
    errors: list[BlockFormatError] = []

    new_text, changed = _format(markdown_text, on_error=errors.append)

    assert new_text == markdown_text
    assert not changed
    assert len(errors) == 1
    assert str(errors[0]).startswith("example.md:8: ")


def test_syntax_error_in_chain_raises_without_on_error():
    markdown_text = (
        "```python\nclass A:\n    x = 1\n```\n"
        + CONTINUES
        + "```python\n    def f(self) return 1\n```\n"
    )

    with pytest.raises(BlockFormatError):
        _format(markdown_text)


def test_a_failing_chain_does_not_stop_other_blocks_formatting():
    markdown_text = (
        "```python\nx=1\n```\n"
        + CONTINUES
        + "```python\ny = (\n```\n\n"
        + "```python\nz=3\n```\n"
    )
    errors: list[BlockFormatError] = []

    new_text, changed = _format(markdown_text, on_error=errors.append)

    assert changed
    assert len(errors) == 1
    assert new_text.startswith("```python\nx=1\n```\n")
    assert new_text.endswith("```python\nz = 3\n```\n")


def test_sentinel_count_change_is_an_error_and_leaves_chain_untouched(monkeypatch):
    def ruff_that_eats_the_sentinels(args, source):
        stdout = "".join(
            line + "\n"
            for line in source.split("\n")
            if line.strip() and not line.startswith("# ")
        )
        return subprocess.CompletedProcess(args, 0, stdout, "")

    monkeypatch.setattr(formatting, "run_ruff", ruff_that_eats_the_sentinels)
    markdown_text = "```python\nx=1\n```\n" + CONTINUES + "```python\ny=2\n```\n"
    errors: list[BlockFormatError] = []

    new_text, changed = _format(markdown_text, on_error=errors.append)

    assert new_text == markdown_text
    assert not changed
    assert len(errors) == 1


def test_skip_marked_block_in_chain_is_context_but_never_rewritten():
    markdown_text = (
        SKIP
        + "```python\nclass A:\n    x=1\n```\n"
        + CONTINUES
        + "```python\n    def f(self):\n      return  1\n```\n"
    )

    new_text, changed = _format(markdown_text)

    assert changed
    assert new_text == (
        SKIP
        + "```python\nclass A:\n    x=1\n```\n"
        + CONTINUES
        + "```python\n    def f(self):\n        return 1\n```\n"
    )


def test_skip_marked_root_still_serves_as_context_for_the_whole_chain():
    markdown_text = (
        SKIP
        + "```python\nclass A:\n    x=1\n```\n"
        + CONTINUES
        + "```python\n    def f(self):\n      return  1\n```\n"
        + CONTINUES
        + "```python\n    def g(self):\n      return  2\n```\n"
    )
    errors: list[BlockFormatError] = []

    new_text, _ = _format(markdown_text, on_error=errors.append)

    assert errors == []
    assert "class A:\n    x=1\n" in new_text
    assert "        return 1\n" in new_text
    assert "        return 2\n" in new_text


def test_syntax_error_in_skip_marked_chain_root_is_not_reported():
    markdown_text = (
        SKIP
        + "```python\nclass A(:\n    x = 1\n```\n"
        + CONTINUES
        + "```python\n    def f(self):\n        return 1\n```\n"
    )
    errors: list[BlockFormatError] = []

    new_text, changed = _format(markdown_text, on_error=errors.append)

    assert errors == []
    assert not changed
    assert new_text == markdown_text


def test_cli_check_passes_on_a_context_only_fragment(tmp_path):
    md = tmp_path / "example.md"
    md.write_text(
        "```python\nclass A:\n    x = 1\n```\n"
        + CONTINUES
        + "```python\n    def f(self):\n        return 1\n```\n",
        encoding="utf-8",
    )

    assert main([str(md), "--check"]) == 0
