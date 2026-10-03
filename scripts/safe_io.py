"""Write private files (mode 600, folder 700) without following symlinks."""
from __future__ import annotations

import os
from pathlib import Path
from typing import TextIO


def ensure_private_dir(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink() or not directory.is_dir():
        raise OSError(f"refusing to use {directory}: not a real directory")
    os.chmod(directory, 0o700)


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
