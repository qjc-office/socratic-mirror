"""Write private files (mode 600, folder 700) without following symlinks."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TextIO


def ensure_private_dir(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink() or not directory.is_dir():
        raise OSError(f"refusing to use {directory}: not a real directory")
    os.chmod(directory, 0o700)


def write_atomic(path: Path, text: str) -> None:
    """Write via a private temp file in the same folder, then rename over path.

    A crash or a concurrent run never leaves a half-written file at path. A symlink
    at path is refused so the caller notices the unexpected setup.
    """
    ensure_private_dir(path.parent)
    if path.is_symlink():
        raise OSError(f"refusing to replace symlink {path}")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def open_private(path: Path, append: bool) -> TextIO:
    """Open path for writing. A symlink at path is refused (O_NOFOLLOW)."""
    ensure_private_dir(path.parent)
    if path.is_symlink():
        raise OSError(f"refusing to write through symlink {path}")
    flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append else os.O_TRUNC)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path), flags, 0o600)
    if hasattr(os, "fchmod"):
        os.fchmod(fd, 0o600)
    return os.fdopen(fd, "a" if append else "w", encoding="utf-8")
