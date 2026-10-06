"""The docstrings are the API reference, so their examples must run and every
public name must have one."""

import doctest
import inspect
from types import ModuleType

import pytest

import jsonrpcserver
from jsonrpcserver import async_main, exceptions, main, response, result

MODULES = [main, async_main, result, exceptions, response]


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__)
def test_docstring_examples(module: ModuleType) -> None:
    outcome = doctest.testmod(module, optionflags=doctest.ELLIPSIS)
    assert outcome.attempted > 0
    assert outcome.failed == 0


@pytest.mark.parametrize("name", jsonrpcserver.__all__)
def test_every_public_name_has_a_docstring(name: str) -> None:
    obj = getattr(jsonrpcserver, name)
    if name == "Result":
        # A typing alias. Its docstring is an attribute docstring in result.py,
        # which the API reference reads from the source.
        assert '"""The return type of a method' in inspect.getsource(result)
    else:
        assert (obj.__doc__ or "").strip(), name
