"""Every Python example in the README and docs must run and show true output."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FILES = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]


@pytest.mark.parametrize("path", FILES, ids=lambda path: path.name)
def test_doc_examples(path: Path) -> None:
    # A fresh interpreter per file, so methods registered with @method on one
    # page don't leak into another.
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "doc_examples.py"), str(path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
