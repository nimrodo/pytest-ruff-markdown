"""`pytest-ruff-markdown-format` on bad input: syntax errors in a Block,
missing paths, and directory walks that must not enter environments.
"""

import pytest

from pytest_ruff_markdown.format import main


def test_syntax_error_block_is_reported_and_other_blocks_are_still_formatted(
    tmp_path, capsys
):
    md = tmp_path / "example.md"
    md.write_text(
        "# Doc\n\n```python\ndef f(:\n```\n\n```python\nx=1\n```\n", encoding="utf-8"
    )

    exit_code = main([str(md)])

    assert exit_code == 2
    assert md.read_text(encoding="utf-8") == (
        "# Doc\n\n```python\ndef f(:\n```\n\n```python\nx = 1\n```\n"
    )
    assert f"{md}:4:" in capsys.readouterr().err


def test_syntax_error_block_makes_check_mode_exit_two(tmp_path):
    md = tmp_path / "example.md"
    md.write_text("```python\ndef f(:\n```\n", encoding="utf-8")

    assert main([str(md), "--check"]) == 2


def test_missing_path_is_a_usage_error(tmp_path, capsys):
    with pytest.raises(SystemExit) as excinfo:
        main([str(tmp_path / "nope.md")])

    assert excinfo.value.code == 2
    assert "nope.md" in capsys.readouterr().err


def test_directory_walk_skips_environments_and_hidden_directories(tmp_path):
    unformatted = "```python\nx=1\n```\n"
    kept = tmp_path / "docs" / "kept.md"
    skipped = [
        tmp_path / ".venv" / "lib" / "a.md",
        tmp_path / ".hidden" / "b.md",
        tmp_path / "node_modules" / "pkg" / "c.md",
        tmp_path / "myenv" / "lib" / "d.md",
    ]
    (tmp_path / "myenv").mkdir()
    (tmp_path / "myenv" / "pyvenv.cfg").write_text("", encoding="utf-8")
    for path in [kept, *skipped]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(unformatted, encoding="utf-8")

    assert main([str(tmp_path)]) == 0

    assert kept.read_text(encoding="utf-8") == "```python\nx = 1\n```\n"
    assert all(p.read_text(encoding="utf-8") == unformatted for p in skipped)


def test_explicit_hidden_directory_argument_is_still_walked(tmp_path):
    md = tmp_path / ".docs" / "a.md"
    md.parent.mkdir()
    md.write_text("```python\nx=1\n```\n", encoding="utf-8")

    assert main([str(tmp_path / ".docs")]) == 0

    assert md.read_text(encoding="utf-8") == "```python\nx = 1\n```\n"
