"""Run the Python examples in Markdown files.

Usage: python tests/doc_examples.py FILE.md [FILE.md ...]

Each file runs in this process with one shared namespace, top to bottom, so
request ids count up from 1 as they do for a reader trying the examples. Run
each file in a fresh interpreter (tests/test_docs.py does).

A python or pycon block that contains ">>>" is a doctest: the output must
match, and "..." matches anything. Any other python block has to run, and if
the next block is a text block titled "Output" (```text title="Output"), what
the code prints must match it.

HTML comments on the lines just before a block change how it runs:
    <!-- requires: ujson -->     skip unless ujson can be imported
    <!-- min-python: 3.10 -->    skip on older Pythons
    <!-- server -->              run the quickstart server
                                 (docs/examples/quickstart.py) on
                                 localhost:8000 while the block runs
    <!-- skip: reason -->        never run it, such as code for 4.x
A block can have several of these, one per line. Fences can be indented, as
they are inside an admonition. Blocks that include a file with "--8<--" are
skipped. Those are the framework examples, which
docs/examples/check_examples.py starts and sends requests to.
"""

import doctest
import importlib.util
import io
import re
import socket
import subprocess
import sys
import time
from contextlib import contextmanager, nullcontext, redirect_stdout
from pathlib import Path
from typing import (
    Any,
    ContextManager,
    Dict,
    Generator,
    List,
    NamedTuple,
    Optional,
    Tuple,
)

QUICKSTART = Path(__file__).parent.parent / "docs" / "examples" / "quickstart.py"
PORT = 8000

# A fence can be indented, for example inside an admonition.
FENCE = re.compile(r"^(\s*)```\s*(\w*)(.*)$")
OUTPUT = re.compile(r'^\s*title="Output"\s*$')
MARKER = re.compile(r"^<!--\s*(requires|min-python|server|skip)(?::\s*(.+?))?\s*-->$")


class Block(NamedTuple):
    line: int
    code: str
    markers: List[str]
    output: Optional[str]


def fenced(lines: List[str], i: int) -> Tuple[str, str, List[str], int]:
    """Read the fenced block starting at line i.

    Return its language, the rest of the opening line, its body without the
    fence's indentation, and the index of the line after the closing fence.
    """
    match = FENCE.match(lines[i])
    assert match
    indent, language, rest = match.groups()
    body: List[str] = []
    i += 1
    while i < len(lines) and not FENCE.match(lines[i]):
        line = lines[i]
        body.append(line[len(indent) :] if line.startswith(indent) else line)
        i += 1
    return language, rest, body, i + 1


def python_blocks(text: str) -> List[Block]:
    blocks: List[Block] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if not FENCE.match(lines[i]):
            i += 1
            continue
        start = i
        language, _, body, i = fenced(lines, i)
        if language in ("python", "py", "pycon"):
            markers: List[str] = []
            j = start - 1
            while j >= 0 and MARKER.match(lines[j].strip()):
                markers.append(lines[j].strip())
                j -= 1
            code = "\n".join(body) + "\n"
            blocks.append(Block(start + 1, code, markers, output_after(lines, i)))
    return blocks


def output_after(lines: List[str], i: int) -> Optional[str]:
    """Return the text of an "Output" block that starts at or after line i."""
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not FENCE.match(lines[i]):
        return None
    language, rest, body, _ = fenced(lines, i)
    if language != "text" or not OUTPUT.match(rest):
        return None
    return "\n".join(body)


def skip_reason(block: Block) -> str:
    if "--8<--" in block.code:
        return "included file"
    for marker in block.markers:
        match = MARKER.match(marker)
        assert match
        kind, value = match.groups()
        if kind == "skip":
            return value or "marked skip"
        if kind == "requires" and not importlib.util.find_spec(value):
            return f"needs {value}"
        if kind == "min-python":
            wanted = tuple(int(part) for part in value.split("."))
            if sys.version_info < wanted:
                return f"needs Python {value}"
    return ""


def port_open() -> bool:
    try:
        with socket.create_connection(("localhost", PORT), timeout=1):
            return True
    except OSError:
        return False


@contextmanager
def quickstart_server() -> Generator[None, None, None]:
    """Run the quickstart server on localhost:8000, as a reader would."""
    if port_open():
        raise RuntimeError(f"Port {PORT} is already in use")
    server = subprocess.Popen(
        [sys.executable, str(QUICKSTART)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        while not port_open():
            if server.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("The quickstart server didn't start")
            time.sleep(0.1)
        yield
    finally:
        server.terminate()
        server.wait(10)


def server_for(block: Block) -> ContextManager[None]:
    if "<!-- server -->" in block.markers:
        return quickstart_server()
    return nullcontext()


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
        with server_for(block):
            failures += run_block(path, block, namespace, runner, parser)
    print(f"{path}: {ran} blocks run, {skipped} skipped, {failures} failed")
    return failures


def run_block(
    path: Path,
    block: Block,
    namespace: Dict[str, Any],
    runner: doctest.DocTestRunner,
    parser: doctest.DocTestParser,
) -> int:
    """Run one block and return the number of failures."""
    if ">>>" in block.code:
        test = parser.get_doctest(
            block.code, namespace, str(path), str(path), block.line
        )
        failed = runner.run(test, clear_globs=False).failed
        # DocTest works on a copy of the namespace. Keep what it defined.
        namespace.update(test.globs)
        return failed
    printed = io.StringIO()
    try:
        with redirect_stdout(printed):
            exec(compile(block.code, f"{path}:{block.line}", "exec"), namespace)
    except Exception as exc:
        print(f"{path}:{block.line}: {type(exc).__name__}: {exc}")
        return 1
    if block.output is not None and printed.getvalue().strip() != block.output.strip():
        print(f"{path}:{block.line}: printed {printed.getvalue()!r}")
        print(f"{' ' * len(str(path))}  expected {block.output!r}")
        return 1
    return 0


if __name__ == "__main__":
    total = sum(run_file(Path(arg)) for arg in sys.argv[1:])
    sys.exit(1 if total else 0)
