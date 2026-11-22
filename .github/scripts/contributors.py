"""Write docs/contributors.md from GitHub's contributor list and the git history.

Usage: GITHUB_TOKEN=$(gh auth token) python .github/scripts/contributors.py

Run it from a full clone of the repository (not a shallow one), on main, then
commit the page if it changed. Without a token, GitHub allows 60 requests an
hour, which isn't enough for every contributor.

Each person on GitHub's contributor list gets one entry, except bots. The
creator comes first, then everyone else by login. Each entry links the
person's first commit on main. If that commit came in a merged pull request
the same person opened, the entry links the pull request instead. The text of
the link is the pull request's or the commit's own title, so the page never
describes anyone's work in words they didn't write.
"""

import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "contributors.md"
API = "https://api.github.com"
CREATOR = "bcb"
CREATOR_NAME = "Beau Barker"
# Characters that would change the Markdown around a title.
MARKDOWN = re.compile(r"([\\`*_\[\]<>|#~])")


@dataclass(frozen=True)
class Entry:
    login: str
    name: str
    title: str
    url: str
    year: str


def repo_slug() -> str:
    match = re.search(r"^repo_name: (\S+)$", (ROOT / "mkdocs.yml").read_text(), re.M)
    if not match:
        raise SystemExit("mkdocs.yml has no repo_name.")
    return match.group(1)


def get(path: str) -> tuple[Any, str]:
    """GET an API path. Returns the decoded JSON and the Link header."""
    request = urllib.request.Request(API + path)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response), response.headers.get("Link") or ""


def next_link(link: str, rel: str) -> str | None:
    match = re.search(rf'<{re.escape(API)}([^>]+)>; rel="{rel}"', link)
    return match.group(1) if match else None


def get_all(path: str) -> list[Any]:
    items: list[Any] = []
    page: str | None = path
    while page:
        data, link = get(page)
        items.extend(data)
        page = next_link(link, "next")
    return items


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def on_main(sha: str) -> bool:
    """Whether this clone has the commit on main."""
    check = ["git", "merge-base", "--is-ancestor", sha, "origin/main"]
    return subprocess.run(check, cwd=ROOT, capture_output=True).returncode == 0


def first_commit(slug: str, login: str) -> str | None:
    """The person's oldest commit on main that isn't a merge commit."""
    query = urllib.parse.urlencode({"author": login, "sha": "main", "per_page": 100})
    data, link = get(f"/repos/{slug}/commits?{query}")
    last = next_link(link, "last")
    if last:
        data, link = get(last)
    # Newest first, so walk back from the end of the last page.
    while True:
        for commit in reversed(data):
            if len(commit["parents"]) <= 1:
                return str(commit["sha"])
        previous = next_link(link, "prev")
        if not previous:
            return None
        data, link = get(previous)


def first_pull(slug: str, login: str) -> dict[str, Any] | None:
    """The person's oldest merged pull request.

    The commit search above misses a squashed commit whose author email names
    an older login of the same account. GitHub still counts it as theirs.
    """
    query = f"repo:{slug} type:pr is:merged author:{login}"
    params = urllib.parse.urlencode({"q": query, "sort": "created", "order": "asc"})
    found, _ = get(f"/search/issues?{params}")
    for item in found["items"]:
        pull: dict[str, Any] = get(f"/repos/{slug}/pulls/{item['number']}")[0]
        sha = pull["merge_commit_sha"]
        if sha and on_main(sha):
            return pull
    return None


def entry(slug: str, login: str) -> Entry:
    user, _ = get(f"/users/{login}")
    sha = first_commit(slug, login)
    pulls: list[dict[str, Any]] = []
    if sha:
        pulls, _ = get(f"/repos/{slug}/commits/{sha}/pulls")
    else:
        pull = first_pull(slug, login)
        if not pull:
            raise SystemExit(f"{login}: no commit or merged pull request found.")
        sha = str(pull["merge_commit_sha"])
        pulls = [pull]
    # The commit must be on main in this clone too, and its title comes from git.
    if not on_main(sha):
        raise SystemExit(f"{login}: {sha} isn't on origin/main. Fetch and retry.")
    title = git("log", "-1", "--format=%s", sha)
    year = git("log", "-1", "--format=%ad", "--date=format:%Y", sha)
    url = f"https://github.com/{slug}/commit/{sha}"
    for pull in pulls:
        if (
            pull.get("merged_at")
            and pull["base"]["repo"]["full_name"] == slug
            and pull["user"]["login"] == login
        ):
            title, url = pull["title"], pull["html_url"]
            break
    name = (user.get("name") or "").strip()
    if name.casefold() == login.casefold():
        name = ""
    return Entry(login, name, title.strip(), url, year)


def escape(text: str) -> str:
    return MARKDOWN.sub(r"\\\1", text)


def person(item: Entry) -> str:
    profile = f"[@{item.login}](https://github.com/{item.login})"
    return f"{escape(item.name)} ({profile})" if item.name else profile


def render(
    project: str, slug: str, creator: Entry, others: list[Entry], unlinked: bool
) -> str:
    lines = [
        "---",
        f"description: Everyone whose changes are in {project}, starting with"
        " its creator Beau Barker, with a link to each person's first merged"
        " change.",
        "---",
        "",
        "<!-- Generated by .github/scripts/contributors.py. Edit the script and",
        "     run it again instead of editing this page. -->",
        "",
        "# Contributors",
        "",
        f"{CREATOR_NAME} ([@{CREATOR}](https://github.com/{CREATOR})) created"
        f" {project}, starting with [{escape(creator.title)}]({creator.url})"
        f" in {creator.year}. Synapse Research has maintained it since"
        " 6 October 2026.",
        "",
        f"Everyone else on GitHub's contributor list for {project} is below, by"
        " GitHub login. Bots are left out. Each link goes to the person's first"
        " change on main, or to the pull request it came in. The link text is"
        " that change's own title.",
        "",
    ]
    for item in others:
        lines.append(
            f"- {person(item)}: [{escape(item.title)}]({item.url}) ({item.year})"
        )
    if unlinked:
        lines += [
            "",
            "Some early commits came from email addresses that aren't linked to"
            " a GitHub account, so GitHub can't list their authors. Their work"
            f" is in the [commit history](https://github.com/{slug}/commits/main/).",
        ]
    lines += [
        "",
        "## How to contribute",
        "",
        "Bug reports and pull requests are welcome."
        " [Contributing](contributing.md) explains how to set up, run the"
        " checks and send a pull request.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    slug = repo_slug()
    project = slug.split("/")[1]
    people = get_all(f"/repos/{slug}/contributors?per_page=100")
    logins = [
        p["login"]
        for p in people
        if p["type"] != "Bot" and not p["login"].endswith("[bot]")
    ]
    if CREATOR not in logins:
        raise SystemExit(f"{CREATOR} isn't on the contributor list.")
    creator = entry(slug, CREATOR)
    others = sorted(
        (entry(slug, login) for login in logins if login != CREATOR),
        key=lambda item: item.login.casefold(),
    )
    # Commits whose email GitHub can't match to an account. Their authors are
    # only named by git, so the page mentions them without listing them.
    known = {CREATOR_NAME.casefold(), *(item.name.casefold() for item in others)}
    everyone = get_all(f"/repos/{slug}/contributors?anon=1&per_page=100")
    unlinked = sorted(
        p["name"]
        for p in everyone
        if p["type"] == "Anonymous" and p["name"].casefold() not in known
    )
    PAGE.write_text(render(project, slug, creator, others, bool(unlinked)))
    left_out = [p["login"] for p in people if p["login"] not in logins]
    print(f"{PAGE.relative_to(ROOT)}: {len(others) + 1} people.")
    print(f"Bots left out: {', '.join(left_out) or 'none'}.")
    print("Commit authors GitHub could not link to an account:", end=" ")
    print(f"{', '.join(unlinked) or 'none'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
