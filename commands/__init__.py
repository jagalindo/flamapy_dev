from .packages import pip
from .repositories import git
from .versions import version
from .make import make
from .docs import docs

__all__ = [
    "docs",
    "git",
    "make",
    "pip",
    "version",
]
