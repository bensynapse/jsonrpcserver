"""Run the Python examples in Markdown files.

Usage: python tests/doc_examples.py FILE.md [FILE.md ...]

Each file runs in this process with one shared namespace, top to bottom, so
request ids count up from 1 as they do for a reader trying the examples. Run
each file in a fresh interpreter (tests/test_docs.py does).

A python block that contains ">>>" is a doctest: the output must match, and
"..." matches anything. Any other python block just has to run.

An HTML comment on the line before a block can skip it:
    <!-- requires: ujson -->     skip unless ujson can be imported
    <!-- min-python: 3.10 -->    skip on older Pythons
Blocks that include a file with "--8<--" are skipped. Those are the transport
examples, which docs/examples/check_examples.py runs against a test server.
"""

import doctest
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, NamedTuple

FENCE = re.compile(r"^```\s*(\w*)\s*$")
MARKER = re.compile(r"^<!--\s*(requires|min-python):\s*(\S+)\s*-->$")


class Block(NamedTuple):
    line: int
    code: str
    marker: str


def python_blocks(text: str) -> List[Block]:
    blocks: List[Block] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = FENCE.match(lines[i])
        if not match:
            i += 1
            continue
        language, start = match.group(1), i
        i += 1
        body: List[str] = []
        while i < len(lines) and not FENCE.match(lines[i]):
            body.append(lines[i])
            i += 1
        i += 1
        if language in ("python", "py", "pycon"):
            marker = lines[start - 1].strip() if start > 0 else ""
            blocks.append(Block(start + 1, "\n".join(body) + "\n", marker))
    return blocks


def skip_reason(block: Block) -> str:
    if "--8<--" in block.code:
        return "included file"
    match = MARKER.match(block.marker)
    if not match:
        return ""
    kind, value = match.groups()
    if kind == "requires":
        return "" if importlib.util.find_spec(value) else f"needs {value}"
    wanted = tuple(int(part) for part in value.split("."))
    return f"needs Python {value}" if sys.version_info < wanted else ""


def run_file(path: Path) -> int:
    namespace: Dict[str, Any] = {"__name__": "__main__"}
    runner = doctest.DocTestRunner(
        optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
    )
    parser = doctest.DocTestParser()
    failures = ran = skipped = 0
    for block in python_blocks(path.read_text()):
        reason = skip_reason(block)
        if reason:
            print(f"{path}:{block.line}: skipped ({reason})")
            skipped += 1
            continue
        ran += 1
        if ">>>" in block.code:
            test = parser.get_doctest(
                block.code, namespace, str(path), str(path), block.line
            )
            failures += runner.run(test, clear_globs=False).failed
            # DocTest works on a copy of the namespace. Keep what it defined.
            namespace.update(test.globs)
        else:
            try:
                exec(compile(block.code, f"{path}:{block.line}", "exec"), namespace)
            except Exception as exc:
                print(f"{path}:{block.line}: {type(exc).__name__}: {exc}")
                failures += 1
    print(f"{path}: {ran} blocks run, {skipped} skipped, {failures} failed")
    return failures


if __name__ == "__main__":
    total = sum(run_file(Path(arg)) for arg in sys.argv[1:])
    sys.exit(1 if total else 0)
