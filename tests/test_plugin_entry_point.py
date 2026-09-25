"""Proves the plugin registers via its pytest11 entry point, not just via import.

Uses runpytest_subprocess() (not runpytest()) because only a real subprocess
boot goes through importlib.metadata entry-point discovery; an in-process run
would skip the exact mechanism this ticket is scaffolding.
"""


def test_plugin_is_discoverable_via_entry_point(pytester):
    result = pytester.runpytest_subprocess("--trace-config")

    result.stdout.fnmatch_lines(["*pytest_ruff_markdown*"])
