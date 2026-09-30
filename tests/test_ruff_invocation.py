"""How the plugin invokes ruff: which binary, with which flags, and how the
Block's source is presented to it (trailing newline, trailing blank lines).

Uses runpytest_subprocess() for the same reason as tests/test_lint.py.
"""


def test_lints_without_ruff_on_path(pytester, monkeypatch):
    pytester.makefile(".md", example="# Doc\n\n```python\nx = 1\n```\n")
    monkeypatch.setenv("PATH", str(pytester.path / "nowhere"))

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)


def test_project_fix_true_does_not_break_reporting(pytester):
    pytester.makepyprojecttoml("[tool.ruff]\nfix = true\n")
    pytester.makefile(".md", example="# Doc\n\n```python\nimport os\nx = 1\n```\n")

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*example.md:4:*F401*"])


def test_single_line_block_has_no_missing_final_newline_violation(pytester):
    pytester.makepyprojecttoml('[tool.ruff.lint]\nselect = ["W"]\n')
    pytester.makefile(".md", example="# Doc\n\n```python\nx = 1\n```\n")

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)


def test_trailing_blank_lines_in_block_are_reported(pytester):
    # W391 is still a preview rule.
    pytester.makepyprojecttoml('[tool.ruff.lint]\npreview = true\nselect = ["W391"]\n')
    pytester.makefile(".md", example="# Doc\n\n```python\nx = 1\n\n\n```\n")

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*example.md:*W391*"])


def test_non_ascii_block_lints_under_a_non_utf8_locale(pytester, monkeypatch):
    for name, value in {
        "LC_ALL": "C",
        "LANG": "C",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONUTF8": "0",
    }.items():
        monkeypatch.setenv(name, value)
    pytester.makefile(".md", example="# Doc\n\n```python\nx = 'café 日本'\n```\n")

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)
