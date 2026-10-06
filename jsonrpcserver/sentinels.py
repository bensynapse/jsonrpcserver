"""Sentinels - these are used to indicate no data is present.

We can't use None, because None may be a valid piece of data.
"""

import sys


class Sentinel:
    """Use this class to create a unique object.

    Has a nicer repr than `object()`.
    """

    # pylint: disable=too-few-public-methods
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"<{sys.intern(str(self.name)).rsplit('.', 1)[-1]}>"


NOCONTEXT = Sentinel("NoContext")
"""The default for `context`: don't pass a context to methods."""
NODATA = Sentinel("NoData")
"""The default for `data` in `Error` and `JsonRpcError`: leave `data` out."""
NOID = Sentinel("NoId")
"""The id of a notification, which has none."""
