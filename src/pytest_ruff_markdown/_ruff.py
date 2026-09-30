"""The single place `ruff` is invoked as a subprocess."""

from __future__ import annotations

import subprocess
import sys


def run_ruff(args: list[str], source: str) -> subprocess.CompletedProcess[str]:
    """Run `ruff <args>` with source on stdin and return the completed process.

    Runs the ruff installed alongside this plugin (`python -m ruff`), not
    whatever `ruff` is first on PATH: PATH may not contain it at all when the
    virtualenv isn't activated, and may hold a different version when it does.
    The encoding is explicit because the locale's isn't necessarily UTF-8.
    """
    return subprocess.run(
        [sys.executable, "-m", "ruff", *args],
        input=source,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
