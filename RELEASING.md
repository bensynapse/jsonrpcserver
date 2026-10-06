# Releasing

Releases are published by `.github/workflows/release.yml` when a tag like
`v5.0.10` is pushed. It builds and checks the sdist and wheel, and attests
their build provenance. Then it uploads them to PyPI with Trusted Publishing
and creates the GitHub release from the CHANGELOG entry. Nobody needs a PyPI
token.

## One-time setup on PyPI

This needs an Owner or Maintainer role on the `jsonrpcserver` project on PyPI.

1. Open https://pypi.org/manage/project/jsonrpcserver/settings/publishing/
2. Under "Add a new publisher", choose **GitHub** and fill in exactly:

   | Field | Value |
   |---|---|
   | Owner | `bensynapse` |
   | Repository name | `jsonrpcserver` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

3. Click "Add".

The `pypi` environment already exists in the GitHub repo settings. It only
accepts deployments from tags matching `v*`. To require a manual approval
before each upload, add yourself under "Required reviewers" in
Settings → Environments → pypi.

## Each release

1. Merge a pull request that gets the version ready:
   - `__version__` in `jsonrpcserver/__init__.py` is the new version.
   - Its CHANGELOG.md heading has the release date instead of "not released
     yet": `## 5.0.10 (2026-10-20)`.
   - The `unreleased` and `pypi_version` lines under `extra` in mkdocs.yml are
     deleted. They show the "not on PyPI yet" banner on every docs page.
     Merging this redeploys the docs, so merge it just before you tag.
   - The paragraph under "Install" in README.md that says the version isn't
     released yet is deleted. The README becomes the PyPI page.
   - For 5.0.10 only: shorten the "If you are on 5.0.9" section of
     `docs/security.md` to a note for people who can't upgrade. The "when it's
     out" wording in README.md and SECURITY.md can go too. `grep -rn "when it's out\|isn't on PyPI" README.md
     SECURITY.md docs` finds them.

   The release workflow checks the first three. It stops if the version and
   tag don't match or the CHANGELOG heading has no date. It also stops if
   mkdocs.yml or README.md still say the version isn't released.
2. Tag the merge commit on main and push the tag:

   ```sh
   git fetch origin
   git tag -a v5.0.10 <commit> -m "5.0.10"
   git push origin v5.0.10
   ```

3. Watch the "Release" workflow in the Actions tab.
4. Check the result:

   ```sh
   curl -s https://pypi.org/pypi/jsonrpcserver/json | python3 -c \
     "import sys, json; i = json.load(sys.stdin)['info']; print(i['version'], i['project_urls'])"
   ```

   The release should have two files, a `.tar.gz` and a `.whl`.

5. If the release fixes a security problem, publish a repository security
   advisory for it, so Dependabot, `pip-audit` and OSV warn people on older
   versions. In the Security tab, choose "New draft security advisory". Set
   the affected versions (for 5.0.10: `>= 5.0.0, <= 5.0.9`) and the patched
   version.
   Pick the CWE, link the docs page that explains it, and publish. For the
   5.0.10 fix, the CWE is CWE-209, information exposure through an error
   message.

## If the upload fails

- `invalid-publisher`: the PyPI publisher settings above don't match. Check
  every field, including the `.yml` in the workflow name.
- `File already exists`: that version is already on PyPI, and PyPI never
  allows the same file twice. Bump the version and tag again.

A failed run can be re-run from the Actions tab once the cause is fixed. If the
tag itself was wrong, delete it locally and on GitHub
(`git push origin :refs/tags/v5.0.10`) before tagging again. Never delete a tag
whose version reached PyPI.

## Docs

The docs site deploys itself from main through `.github/workflows/docs.yml`,
so it changes when the docs change, not at release time. While main is ahead
of PyPI, the `unreleased` setting in mkdocs.yml shows a banner that says so.
The docs also mark features with "New in" or "Changed in" notes.
