"""pytest-ruff-markdown: lints Python code fences in Markdown files via ruff.

Registered as a pytest11 entry point (see pyproject.toml): pytest discovers
plugins by importing this exact module, so `pytest_collect_file` must stay
importable from here even though it's implemented in .plugin.
"""

from __future__ import annotations

from .plugin import pytest_collect_file

__all__ = ["pytest_collect_file"]
