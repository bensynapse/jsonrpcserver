"""dispatch must give the right response to each request when many threads
call it at once. CI runs this on free-threaded 3.14t too."""

import json
import sys
import threading
from typing import Any, Callable, Iterator, List

import pytest

from jsonrpcserver import Error, Result, Success, dispatch, method

THREADS = 8
CALLS = 500


@pytest.fixture(autouse=True)
def frequent_thread_switches() -> Iterator[None]:
    """On GIL builds, switch threads as often as possible to provoke races."""
    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    yield
    sys.setswitchinterval(old)


@method(name="threading_echo")
def echo(value: Any) -> Result:
    return Success(value)


def double(context: int, value: int) -> Result:
    if value < 0:
        return Error(1, "Negative", value)
    return Success(context * value)


def hammer(work: Callable[[int, int], None]) -> List[str]:
    """Run work(thread, call) from several threads at once and collect errors."""
    errors: List[str] = []
    lock = threading.Lock()
    barrier = threading.Barrier(THREADS)

    def worker(thread: int) -> None:
        barrier.wait()
        for call in range(CALLS):
            try:
                work(thread, call)
            except Exception as exc:
                with lock:
                    errors.append(repr(exc))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return errors


def test_global_methods_from_many_threads() -> None:
    def work(thread: int, call: int) -> None:
        id_ = thread * CALLS + call
        request = {"jsonrpc": "2.0", "method": "threading_echo", "params": [id_]}
        response = json.loads(dispatch(json.dumps({**request, "id": id_})))
        assert response == {"jsonrpc": "2.0", "result": id_, "id": id_}

    assert hammer(work) == []


def test_batches_and_context_from_many_threads() -> None:
    def work(thread: int, call: int) -> None:
        batch = [
            {"jsonrpc": "2.0", "method": "double", "params": [call], "id": 1},
            {"jsonrpc": "2.0", "method": "double", "params": [-1], "id": 2},
            {"jsonrpc": "2.0", "method": "double", "params": [call]},
        ]
        response = dispatch(
            json.dumps(batch),
            {"double": double},
            context=thread,
            max_batch_size=3,
        )
        assert json.loads(response) == [
            {"jsonrpc": "2.0", "result": thread * call, "id": 1},
            {
                "jsonrpc": "2.0",
                "error": {"code": 1, "message": "Negative", "data": -1},
                "id": 2,
            },
        ]

    assert hammer(work) == []
