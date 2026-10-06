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

1. Merge a pull request that sets `__version__` in `jsonrpcserver/__init__.py`
   and adds a `## <version>` section to CHANGELOG.md. The release workflow
   fails if either is missing or they don't match the tag.
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
so it changes when the docs change, not at release time.
