# Contributing

Bug reports and pull requests are welcome. For a bigger change, open an issue
first so we can agree on the approach. Breaking changes wait for 6.0. See the
[roadmap](https://bensynapse.github.io/jsonrpcserver/roadmap/).

## Setting up

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e . -r requirements/test.txt -r requirements/lint.txt
```

## Checks

CI runs these, and a pull request needs all of them to pass:

```sh
pytest --cov          # tests, 100% line and branch coverage required
ruff check .
ruff format --check .
mypy
pyright
```

To run the tests on every Python version you have installed, use `tox`.

## Docs

The docs are in `docs/`, built with MkDocs. To preview them:

```sh
pip install -r requirements/docs.txt
mkdocs serve
```

`tests/test_docs.py` runs every Python block in the README and docs, so keep
the shown output accurate. The framework examples are files in
`docs/examples/`. To run them against real servers, install
`requirements/examples.txt` and run `python docs/examples/check_examples.py`.
They listen on port 5000, so free it first.

## Pull requests

- Keep each pull request to one change, with a test for it.
- Add a line to CHANGELOG.md if users will notice the change.
- 5.x supports Python 3.8 and later, and its public API must not change.
  That includes the names importable from each module, not just
  `jsonrpcserver` itself.
