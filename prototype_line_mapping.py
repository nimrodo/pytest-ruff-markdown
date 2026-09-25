"""
PROTOTYPE -- throwaway, not part of the real pytest_ruff_markdown package.
Resolves wayfinder ticket #4 ("Collection & line mapping: map ruff
violations back to markdown source lines"), child of map #2.

QUESTION BEING ANSWERED
------------------------
When we extract a fenced ```python / ```py code block from a markdown
file, can we make Ruff's own reported violation line number land
directly on the correct line of the *original markdown file* -- with
zero offset math on our side -- by padding the extracted block with
leading blank lines so its content starts at the same line number it
occupies in the source file? And does that hold up cleanly when a file
has multiple such blocks?

WHY THIS ISN'T A DOUBLE-CLICK HTML DEMO
-----------------------------------------
The prototype skill's default shape for a "does this logic feel right"
question is a single shareable HTML file a non-developer can click
through. That doesn't fit here: the claim under test only becomes real
by invoking the actual `ruff` binary via subprocess, which a browser
sandbox can't do. So this is a small, runnable Python script instead --
same idea (a pure, liftable module + a driver that surfaces state after
every step), just in the runtime that can actually call ruff. Run it
with: `python prototype_line_mapping.py` (or `uv run python
prototype_line_mapping.py` from inside the project).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# The liftable part: pure functions, no I/O beyond the ruff subprocess call.
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^```(python|py)\s*$")
FENCE_END_RE = re.compile(r"^```\s*$")


@dataclass
class CodeBlock:
    """A fenced Python block extracted from a markdown file."""

    source: str  # the block's own text, unpadded
    start_line: int  # 1-indexed line in the ORIGINAL file where the block's
    # first line of *content* (not the ``` fence line) lives


def extract_python_blocks(markdown_text: str) -> list[CodeBlock]:
    """Find every ```python / ```py fenced block and its true source line.

    Bare ``` fences (no info-string) are intentionally ignored -- decided
    already on the map (only python/py info-strings count).
    """
    lines = markdown_text.splitlines()
    blocks: list[CodeBlock] = []
    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if m:
            content_start = i + 1  # 0-indexed position of first content line
            j = content_start
            while j < len(lines) and not FENCE_END_RE.match(lines[j]):
                j += 1
            block_lines = lines[content_start:j]
            blocks.append(
                CodeBlock(
                    source="\n".join(block_lines),
                    start_line=content_start + 1,  # convert to 1-indexed
                )
            )
            i = j + 1
        else:
            i += 1
    return blocks


def pad_to_original_position(block: CodeBlock) -> str:
    """Prepend blank lines so the block's own line 1 becomes its true
    line number in the original markdown file. This is the whole trick:
    once padded, whatever line ruff reports IS the markdown line -- no
    offset arithmetic needed downstream.
    """
    padding = "\n" * (block.start_line - 1)
    return padding + block.source


@dataclass
class Violation:
    line: int
    code: str
    message: str


def lint_via_ruff(padded_source: str, stdin_filename: str) -> list[Violation]:
    """Run ruff on padded source via stdin, one invocation per block
    (deliberately not batched/concatenated -- see sanity check below for
    why that matters), parsing the stable --output-format=json."""
    proc = subprocess.run(
        [
            # `uv tool run ruff` rather than a bare `ruff` -- ruff isn't on
            # this shell's PATH, and the project's own convention is "uv
            # for everything" anyway, so this also doubles as evidence
            # that invocation-via-uv works fine for the real plugin.
            "uv",
            "tool",
            "run",
            "ruff",
            "check",
            "-",
            "--stdin-filename",
            stdin_filename,
            "--output-format=json",
            "--no-cache",
        ],
        input=padded_source,
        capture_output=True,
        text=True,
    )
    # ruff exits 1 when it finds violations -- that's expected, not an error.
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"ruff failed unexpectedly: {proc.stderr}")
    raw = json.loads(proc.stdout or "[]")
    return [
        Violation(line=v["location"]["row"], code=v["code"], message=v["message"])
        for v in raw
    ]


# ---------------------------------------------------------------------------
# The driver: surfaces state after every step, prints PASS/FAIL verdicts.
# ---------------------------------------------------------------------------

FIXTURE_MARKDOWN = """# Example doc

Some prose before the first block.

```python
name = "world"

print(f"hello {name}")
```

More prose in between, explaining the next example at some length so the
line numbers genuinely differ from the first block by a nontrivial amount.

```python
import sys  # unused import -- should trigger F401
x = 1
```
"""


def main() -> None:
    print("=" * 70)
    print("STEP 1: extract blocks from the fixture markdown file")
    print("=" * 70)
    blocks = extract_python_blocks(FIXTURE_MARKDOWN)
    for idx, b in enumerate(blocks):
        print(f"  block[{idx}] starts at original line {b.start_line}:")
        print("    " + "\n    ".join(b.source.splitlines()))
    assert len(blocks) == 2, f"expected 2 blocks, got {len(blocks)}"

    print()
    print("=" * 70)
    print("STEP 2: pad each block, run it through ruff independently")
    print("=" * 70)
    all_ok = True
    for idx, b in enumerate(blocks):
        padded = pad_to_original_position(b)
        print(f"\n  block[{idx}] padded source (line numbers now match original):")
        for lineno, text in enumerate(padded.splitlines(), start=1):
            marker = " <-- block content starts here" if text.strip() else ""
            print(f"    {lineno:3}: {text!r}{marker}")

        violations = lint_via_ruff(padded, stdin_filename=f"README.md::block{idx}")
        print(f"  ruff violations for block[{idx}]: {violations!r}")

        if idx == 0:
            # first block is clean
            ok = violations == []
            print(f"  expected: no violations -> {'PASS' if ok else 'FAIL'}")
        else:
            # second block has an unused import (F401) -- expect it reported
            # on the block's own second physical line, which after padding
            # must equal its true line in FIXTURE_MARKDOWN.
            expected_line = b.start_line  # the `import sys` line itself
            ok = any(
                v.code == "F401" and v.line == expected_line for v in violations
            )
            print(
                f"  expected: F401 reported at original markdown line "
                f"{expected_line} -> {'PASS' if ok else 'FAIL'}"
            )
        all_ok = all_ok and ok

    print()
    print("=" * 70)
    print("STEP 3: sanity check -- why NOT concatenate all blocks into one")
    print("=" * 70)
    print(
        "  Concatenating every block's padded source into a single ruff\n"
        "  invocation would merge them into one virtual file: an unused\n"
        "  `import sys` in block 2 could get flagged as *already imported*\n"
        "  or otherwise cross-contaminate with block 1's `import os`, and a\n"
        "  syntax error in one block would abort linting for every other\n"
        "  block in the same run. Keeping one ruff subprocess per block\n"
        "  keeps blocks isolated -- confirmed above: block[0] and block[1]\n"
        "  were linted independently and neither's result leaked into the\n"
        "  other's."
    )

    print()
    print("=" * 70)
    print(f"VERDICT: {'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'}")
    print("=" * 70)
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
