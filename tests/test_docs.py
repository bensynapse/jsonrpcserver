"""Every Python example in the README and docs must run and show true output.

The framework examples run in CI's docs job, which has the frameworks
installed. The checks here keep the docs complete and in step with the code.
"""

import re
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

import pytest

import jsonrpcserver

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
FILES = [ROOT / "README.md", *sorted(DOCS.rglob("*.md"))]

# The constants that docs/examples/check_examples.py tests against.
CHECKER = runpy.run_path(str(DOCS / "examples" / "check_examples.py"))
CURL: str = CHECKER["CURL"]
CURL_OUTPUT: str = CHECKER["CURL_OUTPUT"]
EXAMPLES: Dict[str, Any] = CHECKER["EXAMPLES"]
NOT_SERVERS: Set[str] = CHECKER["NOT_SERVERS"]


@pytest.mark.parametrize("path", FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_doc_examples(path: Path) -> None:
    # A fresh interpreter per file, so methods registered with @method on one
    # page don't leak into another.
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "doc_examples.py"), str(path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def block_after(text: str, after: str, language: str) -> str:
    fence = f"```{language}\n"
    start = text.index(fence, text.index(after)) + len(fence)
    return text[start : text.index("```", start)]


def test_readme_quickstart_is_the_tested_example() -> None:
    """check_examples.py runs quickstart.py, so the README must match it."""
    readme = (ROOT / "README.md").read_text()
    example = (DOCS / "examples" / "quickstart.py").read_text()
    assert block_after(readme, "## Quickstart", "python") == example
    assert block_after(readme, "## Quickstart", "text") == CURL_OUTPUT + "\n"


@pytest.mark.parametrize("path", FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_every_curl_command_is_the_tested_one(path: Path) -> None:
    """check_examples.py runs CURL against the quickstart server."""
    for line in path.read_text().splitlines():
        if line.startswith("curl "):
            assert line == CURL


def test_every_included_example_is_checked() -> None:
    included: Set[str] = set()
    for path in DOCS.rglob("*.md"):
        included.update(
            re.findall(r'--8<-- "docs/examples/(\w+\.py)"', path.read_text())
        )
    assert included
    assert included <= set(EXAMPLES) | NOT_SERVERS
    # Every example server is shown somewhere in the docs.
    assert set(EXAMPLES) <= included


def test_examples_use_port_8000_on_localhost() -> None:
    for path in (DOCS / "examples").glob("*.py"):
        text = path.read_text()
        assert "5000" not in text, path.name
        assert "tcp://*" not in text, path.name


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_examples_set_max_batch_size(name: str) -> None:
    """The Security page says to set it on every dispatch call."""
    text = (DOCS / "examples" / name).read_text()
    calls = re.findall(r"dispatch\((.*)\)", text)
    if name == "quickstart.py":
        # serve() calls dispatch itself.
        assert calls == []
    else:
        assert calls
        assert all("max_batch_size=100" in call for call in calls), calls


def public_names() -> List[str]:
    return [*jsonrpcserver.__all__, "__version__"]


@pytest.mark.parametrize("name", public_names())
def test_reference_documents_every_public_name(name: str) -> None:
    reference = (DOCS / "reference.md").read_text()
    assert f"::: jsonrpcserver.{name}\n" in reference


def test_python_versions_badge_matches_classifiers() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()
    versions = re.findall(r'"Programming Language :: Python :: (3\.\d+)"', pyproject)
    readme = (ROOT / "README.md").read_text()
    badge = re.search(r"img\.shields\.io/badge/python-([^-]+)-blue", readme)
    assert badge
    assert badge.group(1).split("%20%7C%20") == versions


def test_tagline_is_the_same_everywhere() -> None:
    tagline = "Process incoming JSON-RPC 2.0 requests in Python"
    assert f'description = "{tagline}"' in (ROOT / "pyproject.toml").read_text()
    assert f"site_description: {tagline}\n" in (ROOT / "mkdocs.yml").read_text()
    assert f"<i>{tagline}</i>" in (ROOT / "README.md").read_text()
    assert f"_{tagline}._" in (DOCS / "index.md").read_text()


def test_every_page_has_a_description() -> None:
    for path in DOCS.rglob("*.md"):
        text = path.read_text()
        assert text.startswith("---\n"), path
        front_matter = text.split("---\n")[1]
        assert re.search(r"^description: .{50,}$", front_matter, re.M), path


def test_old_domains_are_named_not_linked() -> None:
    """The FAQ names the old domains so readers recognise them. CI's domain
    check skips that file, so make sure they're never links."""
    faq = (DOCS / "faq.md").read_text()
    for match in re.finditer(r"jsonrpc(?:client|server)\.com", faq):
        before = faq[max(0, match.start() - 12) : match.start()]
        assert "://" not in before and "](" not in before and "www." not in before
