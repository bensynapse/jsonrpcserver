"""Fail if built package metadata mentions a domain we lost control of.

jsonrpcclient.com and jsonrpcserver.com were the project's old websites. Both
domains now belong to someone else and serve gambling spam, and PyPI shows
whatever links are in the metadata. composed.blog, the previous author's
blog, now redirects to spam as well. The long description (README) is part of
the metadata, so this checks that too.

Usage: python check_metadata.py dist/*
"""

import re
import sys
import tarfile
import zipfile
from pathlib import Path

FORBIDDEN = re.compile(r"jsonrpc(client|server)\.com|composed\.blog", re.IGNORECASE)


def read_metadata(path: Path) -> str:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as wheel:
            name = next(
                n for n in wheel.namelist() if n.endswith(".dist-info/METADATA")
            )
            return wheel.read(name).decode()
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path) as sdist:
            member = next(
                m
                for m in sdist.getmembers()
                if m.name.count("/") == 1 and m.name.endswith("/PKG-INFO")
            )
            data = sdist.extractfile(member)
            assert data is not None
            return data.read().decode()
    raise SystemExit(f"Don't know how to read {path}")


def main(paths: list) -> int:
    if not paths:
        print("No distribution files given")
        return 1
    failed = False
    for path in map(Path, paths):
        text = read_metadata(path)
        print(f"{path.name}:")
        for line in text.splitlines():
            if line.startswith(
                ("Version:", "Project-URL:", "Home-page:", "Requires-Python:")
            ):
                print(f"  {line}")
        for number, line in enumerate(text.splitlines(), 1):
            if FORBIDDEN.search(line):
                print(f"  ERROR line {number}: {line.strip()}")
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
