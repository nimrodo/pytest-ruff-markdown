"""Guards the ruff runtime dependency floor decided on the wayfinder map (#3)."""

import tomllib
from pathlib import Path


def test_ruff_is_a_declared_runtime_dependency():
    pyproject = tomllib.loads(
        Path(__file__).parent.parent.joinpath("pyproject.toml").read_text()
    )

    dependencies = pyproject["project"]["dependencies"]

    assert any(dep.startswith("ruff>=0.4.0") for dep in dependencies)
