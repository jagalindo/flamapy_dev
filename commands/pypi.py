"""
PyPI package availability utilities for flamapy-dev.

This module provides utilities for checking package availability on PyPI
and waiting for dependencies to be published.
"""

import json
import os
import time
from urllib import error, request

from packaging.requirements import InvalidRequirement, Requirement

HTTP_OK = 200


def _parse_requirements(req_file: str) -> list[Requirement]:
    """
    Parse a requirements.txt file and return a list of Requirement objects.

    Args:
        req_file: Path to the requirements.txt file.

    Returns:
        List of packaging.requirements.Requirement objects.
    """
    requirements: list[Requirement] = []
    if not os.path.exists(req_file):
        return requirements
    with open(req_file, "r", encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                requirements.append(Requirement(stripped))
            except InvalidRequirement:
                continue
    return requirements


def _package_available(req: Requirement) -> bool:
    """
    Check if a package version is available on PyPI.

    Args:
        req: A Requirement object specifying the package and version constraints.

    Returns:
        True if the package version is available on PyPI, False otherwise.
    """
    url = f"https://pypi.org/pypi/{req.name}/json"
    try:
        with request.urlopen(url, timeout=10) as resp:
            if resp.status != HTTP_OK:
                return False
            data = json.load(resp)
    except (error.URLError, json.JSONDecodeError, OSError):
        return False
    if not req.specifier:
        return True
    releases = data.get("releases", {})
    for ver in releases.keys():
        try:
            if req.specifier.contains(ver, prereleases=True):
                return True
        except ValueError:
            continue
    return False


def wait_for_requirements(req_file: str, check_interval: int = 10) -> None:
    """
    Block until all requirements from a file are available on PyPI.

    This function is useful when releasing packages that depend on each other,
    ensuring that dependencies are published before dependent packages are tagged.

    Args:
        req_file: Path to the requirements.txt file.
        check_interval: Seconds to wait between PyPI checks (default: 10).
    """
    requirements = _parse_requirements(req_file)
    if not requirements:
        return
    while True:
        if all(_package_available(r) for r in requirements):
            return
        time.sleep(check_interval)
