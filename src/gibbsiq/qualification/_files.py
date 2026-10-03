"""Durable replacement of qualification evidence metadata."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


def atomic_bytes(target: Path, payload: bytes) -> None:
    """Replace a file after flushing a unique temporary file in its directory.

    Callers own path validation and their distinct retained-byte budgets.
    """
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, prefix=target.name + ".", suffix=".tmp", delete=False
        ) as stream:
            temporary = stream.name
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
