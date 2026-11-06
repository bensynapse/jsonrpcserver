"""The sync and async dispatch functions take the same options, with the same
defaults (plans/6.0.md, D9). max_concurrency is async only: dispatch runs a batch one
request at a time."""

import inspect

import pytest

from jsonrpcserver import async_main, main

ASYNC_ONLY = {"max_concurrency"}


@pytest.mark.parametrize(
    "name", ["dispatch_to_response", "dispatch_to_serializable", "dispatch_to_json"]
)
def test_sync_and_async_options_match(name: str) -> None:
    sync = inspect.signature(getattr(main, name)).parameters
    async_ = {
        option: parameter
        for option, parameter in inspect.signature(
            getattr(async_main, name)
        ).parameters.items()
        if option not in ASYNC_ONLY
    }
    assert list(sync) == list(async_)
    for option in sync:
        assert (sync[option].kind, sync[option].default) == (
            async_[option].kind,
            async_[option].default,
        ), option
