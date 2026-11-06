"""Build the docs site with one copy of the docs per release line.

Usage: python .github/scripts/build_versions.py OUT_DIR [--from-branch VERSION]

Each line in LINES is built from its newest release tag. The stable line is the
newest one with a final release (not a/b/rc). Its docs go at the site root, so
the addresses that PyPI, the README and old posts link to keep working. Every
line, the stable one too, also gets its own folder (/5.x/, /6.0/), and
versions.json lists them for the version menu.

Search engines should only see the root copy. So every copy is built with the
root's site_url, which makes each canonical link and sitemap entry point at the
root. A page that only exists in another version gets a noindex tag instead of
a canonical link. check() fails the build if any of this doesn't hold.

--from-branch 5.x builds that line from its branch instead of its tag, to
publish a docs-only fix between releases. RELEASING.md explains when.

The site needs this script and version-selector.js from the commit that runs
it, and nothing new from the tags. So old tags build the same way as new ones.
"""

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

LIVE = "https://bensynapse.github.io/jsonrpcserver/"
SELECTOR = Path(__file__).with_name("version-selector.js")
REQUIREMENTS = ["requirements/docs.txt", "requirements/docs-constraints.txt"]
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$")
PRE_RELEASE = {"a": "alpha", "b": "beta", "rc": "release candidate"}


@dataclass(frozen=True)
class Line:
    """A release line: its folder on the site, its tags and its branch."""

    version: str
    tag_prefix: str
    branch: str


# Newest first. To start a new line, add it at the top. Its docs appear as a
# pre-release once it has an a/b/rc tag, and become stable with the first
# final release.
LINES = [
    Line("6.0", "v6.0.", "main"),
    Line("5.x", "v5.", "release/5.x"),
]


@dataclass(frozen=True)
class Build:
    line: Line
    ref: str
    title: str
    stable: bool


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def tag_key(tag: str) -> tuple[int, int, int, int, int]:
    match = TAG.match(tag)
    assert match
    major, minor, patch, kind, number = match.groups()
    # A final release sorts after its own pre-releases.
    pre = (["a", "b", "rc"].index(kind), int(number)) if kind else (3, 0)
    return int(major), int(minor), int(patch), *pre


def plan(tags: list[str], from_branch: str | None) -> list[Build]:
    """Pick the ref and title for each line, newest line first."""
    tags = [t for t in tags if TAG.match(t)]
    builds: list[Build] = []
    stable_found = False
    for line in LINES:
        ours = sorted((t for t in tags if t.startswith(line.tag_prefix)), key=tag_key)
        finals = [t for t in ours if not TAG.match(t).group(4)]  # type: ignore[union-attr]
        if finals:
            tag, title = finals[-1], line.version
        elif ours and not stable_found:
            # Only pre-releases so far, and newer than the stable line.
            tag = ours[-1]
            kind = TAG.match(tag).group(4)  # type: ignore[union-attr]
            title = f"{line.version} ({PRE_RELEASE[kind]})"
        else:
            continue
        ref = f"origin/{line.branch}" if from_branch == line.version else tag
        stable = bool(finals) and not stable_found
        stable_found = stable_found or stable
        builds.append(Build(line, ref, title, stable))
    if not stable_found:
        raise SystemExit("No line in LINES has a final release tag.")
    if from_branch and from_branch not in {b.line.version for b in builds}:
        raise SystemExit(f"--from-branch {from_branch}: no such version on the site.")
    return builds


class Loader(yaml.SafeLoader):
    """Read mkdocs.yml without failing on tags like !!python/name."""


Loader.add_multi_constructor("", lambda loader, suffix, node: None)


def export(ref: str, into: Path) -> None:
    """Write the files of ref into a directory, without its git history."""
    archive = subprocess.run(
        ["git", "archive", "--format=tar", ref], check=True, capture_output=True
    ).stdout
    into.mkdir(parents=True)
    with tempfile.TemporaryFile() as tmp:
        tmp.write(archive)
        tmp.seek(0)
        with tarfile.open(fileobj=tmp) as tar:
            tar.extractall(into, filter="data")


def python_for(tree: Path, work: Path) -> str:
    """This Python if the tree pins the same docs toolchain, else a new venv."""
    here = Path.cwd()
    digest = hashlib.sha256()
    same = True
    for name in REQUIREMENTS:
        theirs = (tree / name).read_bytes()
        digest.update(theirs)
        same = same and (here / name).exists() and (here / name).read_bytes() == theirs
    if same:
        return sys.executable
    venv = work / f"venv-{digest.hexdigest()[:12]}"
    python = venv / "bin" / "python"
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "-q",
                "-r",
                str(tree / REQUIREMENTS[0]),
            ],
            check=True,
        )
    return str(python)


def build(item: Build, tree: Path, out: Path, python: str) -> None:
    parent = yaml.load((tree / "mkdocs.yml").read_text(), Loader=Loader)
    shutil.copy(SELECTOR, tree / "docs" / "assets" / SELECTOR.name)
    child: dict[str, Any] = {
        "INHERIT": "mkdocs.yml",
        "site_url": LIVE,
        "edit_uri": f"edit/{item.line.branch}/docs/",
        "extra_javascript": [
            *(parent.get("extra_javascript") or []),
            f"assets/{SELECTOR.name}",
        ],
    }
    config = tree / "mkdocs.versioned.yml"
    config.write_text(yaml.safe_dump(child, sort_keys=False))
    print(f"Building {item.title} from {item.ref} into {out}", flush=True)
    subprocess.run(
        [
            python,
            "-m",
            "mkdocs",
            "build",
            "--strict",
            "-q",
            "-f",
            str(config),
            "-d",
            str(out),
        ],
        check=True,
        cwd=tree,
    )


CANONICAL = re.compile(r'<link rel="canonical" href="([^"]*)">')
OG_URL = re.compile(r'\s*<meta property="og:url" content="[^"]*">')


def root_file(out: Path, url: str) -> Path | None:
    """The file at the site root that a live URL points at, if there is one."""
    if not url.startswith(LIVE):
        return None
    path = out / url[len(LIVE) :]
    return path / "index.html" if url.endswith("/") else path


def point_at_root(out: Path, folder: Path) -> None:
    """Keep each page's canonical link only if the root has that page."""
    for page in folder.rglob("*.html"):
        text = page.read_text()
        match = CANONICAL.search(text)
        if not match:
            continue
        target = root_file(out, html.unescape(match.group(1)))
        if target and target.is_file():
            continue
        text = CANONICAL.sub('<meta name="robots" content="noindex">', text, count=1)
        page.write_text(OG_URL.sub("", text, count=1))


def main(out: Path, from_branch: str | None) -> int:
    builds = plan(git("tag", "--list", "v*").split(), from_branch)
    if out.exists():
        shutil.rmtree(out)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for item in builds:
            tree = work / item.line.version
            export(item.ref, tree)
            build(item, tree, out / item.line.version, python_for(tree, work))
    stable = next(item for item in builds if item.stable)
    shutil.copytree(out / stable.line.version, out, dirs_exist_ok=True)
    versions = [
        {
            "version": item.line.version,
            "title": item.title,
            "aliases": ["stable", "latest"] if item.stable else [],
        }
        for item in builds
    ]
    (out / "versions.json").write_text(json.dumps(versions, indent=2) + "\n")
    for item in builds:
        point_at_root(out, out / item.line.version)
    problems = check(out)
    for problem in problems:
        print(problem)
    print(json.dumps(versions))
    return 1 if problems else 0


def page_config(text: str) -> dict[str, Any]:
    match = re.search(r'<script id="__config"[^>]*>(.*?)</script>', text, re.S)
    return json.loads(match.group(1)) if match else {}


def check(out: Path) -> list[str]:
    """What must hold for the assembled site. Returns the problems found."""
    problems: list[str] = []
    versions = json.loads((out / "versions.json").read_text())
    folders = [v["version"] for v in versions]
    stable = [v for v in versions if "stable" in v["aliases"]]
    if len(stable) != 1 or "latest" not in stable[0]["aliases"]:
        problems.append("versions.json: one version must be stable and latest")
    under_folder = tuple(f"{LIVE}{f}/" for f in folders)
    for folder in ["", *folders]:
        if not (out / folder / "index.html").is_file():
            problems.append(f"/{folder}: no index.html")
        sitemap = (out / folder / "sitemap.xml").read_text()
        for url in re.findall(r"<loc>(.*?)</loc>", sitemap):
            if not url.startswith(LIVE) or url.startswith(under_folder):
                problems.append(f"/{folder} sitemap lists {url}, not a root page")
            elif not folder:
                target = root_file(out, url)
                if not target or not target.is_file():
                    problems.append(f"sitemap.xml lists {url}, which doesn't exist")
    for page in sorted(out.rglob("*.html")):
        name = page.relative_to(out).as_posix()
        if page.name == "404.html":
            continue
        text = page.read_text()
        if page_config(text).get("version"):
            # At the root, Material would look for versions.json outside the site.
            problems.append(f"{name}: extra.version is set, use version-selector.js")
        if SELECTOR.name not in text:
            problems.append(f"{name}: no {SELECTOR.name}")
        match = CANONICAL.search(text)
        if not match:
            if 'content="noindex"' not in text:
                problems.append(f"{name}: no canonical link and no noindex")
            continue
        url = html.unescape(match.group(1))
        target = root_file(out, url)
        if url.startswith(under_folder) or not target or not target.is_file():
            problems.append(f"{name}: canonical {url} is not a page at the root")
    return problems


def parse_args(argv: list[str]) -> tuple[Path, str | None]:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--from-branch", default="", help="a version folder, e.g. 5.x")
    args = parser.parse_args(argv)
    return args.out.resolve(), args.from_branch or None


if __name__ == "__main__":
    sys.exit(main(*parse_args(sys.argv[1:])))
