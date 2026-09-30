"""Fence tracking in `extract_python_blocks`: a Block's closing fence follows
CommonMark (same character, at least as long as the opener, up to 3 spaces of
indent), and a python fence nested inside any other fence is literal text, not
a Block.
"""

from pytest_ruff_markdown.blocks import extract_python_blocks


def _sources(markdown_text: str) -> list[str]:
    return [block.source for block in extract_python_blocks(markdown_text)]


def test_closing_fence_longer_than_opener_closes_the_block():
    blocks = extract_python_blocks(
        "```python\nx=1\n````\n\ntext\n\n```python\ny=2\n```\n"
    )

    assert [b.source for b in blocks] == ["x=1", "y=2"]
    assert [b.start_line for b in blocks] == [2, 8]


def test_closing_fence_indented_up_to_three_spaces_closes_the_block():
    assert _sources("```python\nx=1\n   ```\ntext\n") == ["x=1"]


def test_closing_fence_indented_four_spaces_is_block_content():
    assert _sources("```python\nx=1\n    ```\n```\n") == ["x=1\n    ```"]


def test_shorter_closing_fence_does_not_close_a_longer_opener():
    assert _sources("````python\nx=1\n```\ny=2\n````\n") == ["x=1\n```\ny=2"]


def test_closing_fence_with_an_info_string_does_not_close_the_block():
    assert _sources("```python\nx=1\n```bash\ny=2\n```\n") == ["x=1\n```bash\ny=2"]


def test_python_fence_inside_a_longer_backtick_fence_is_not_a_block():
    assert _sources("````markdown\n```python\nx=1\n```\n````\n") == []


def test_python_fence_inside_a_tilde_fence_is_not_a_block():
    assert _sources("~~~markdown\n```python\nx=1\n```\n~~~\n") == []


def test_python_fence_inside_a_bare_fence_is_not_a_block():
    assert _sources("```\n```python\n```\nx=1\n```\n") == []


def test_block_after_a_non_python_fence_is_collected_with_correct_line():
    blocks = extract_python_blocks("```bash\necho hi\n```\n```python\nx=1\n```\n")

    assert [b.source for b in blocks] == ["x=1"]
    assert blocks[0].start_line == 5


def test_longer_backtick_python_fence_is_a_block():
    assert _sources("````python\nx = '```'\n````\n") == ["x = '```'"]


def test_tilde_python_fence_is_still_not_collected():
    assert _sources("~~~python\nx=1\n~~~\n") == []
