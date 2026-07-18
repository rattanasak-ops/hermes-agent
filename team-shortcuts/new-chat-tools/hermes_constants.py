"""Small Python 3.9 compatible home resolver for portable Worktree tools."""

from pathlib import Path
import os


def get_hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser().resolve()
