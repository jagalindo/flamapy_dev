"""
PyPI package availability utilities for flamapy-dev.

This module provides utilities for checking package availability on PyPI
and waiting for dependencies to be published.
"""

import json
import os
import re
import ssl
import time
from urllib import error, request

import certifi
from packaging.requirements import InvalidRequirement, Requirement

HTTP_OK = 200
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


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


def _parse_pyproject_requirements(pyproject_file: str) -> list[Requirement]:
    """
    Parse versioned dependencies from a pyproject.toml file.

    Reads the [project] dependencies array and returns a list of
    Requirement objects for entries that have a version specifier.

    Args:
        pyproject_file: Path to the pyproject.toml file.

    Returns:
        List of packaging.requirements.Requirement objects.
    """
    requirements: list[Requirement] = []
    if not os.path.exists(pyproject_file):
        return requirements
    with open(pyproject_file, "r", encoding="utf-8") as f:
        text = f.read()
    for m in re.finditer(r'"([a-zA-Z0-9_-]+[~>=<][^"]+)"', text):
        try:
            requirements.append(Requirement(m.group(1)))
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
        with request.urlopen(url, timeout=10, context=_SSL_CONTEXT) as resp:
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


def wait_for_pyproject_requirements(pyproject_file: str, check_interval: int = 10) -> None:
    """
    Block until all versioned dependencies in a pyproject.toml are available on PyPI.

    This function is useful when releasing packages that depend on each other,
    ensuring that dependencies are published before dependent packages are tagged.

    Args:
        pyproject_file: Path to the pyproject.toml file.
        check_interval: Seconds to wait between PyPI checks (default: 10).
    """
    requirements = _parse_pyproject_requirements(pyproject_file)
    if not requirements:
        return
    while True:
        if all(_package_available(r) for r in requirements):
            return
        time.sleep(check_interval)


def get_internal_requirements(
        pyproject_file: str, internal_packages: set[str]) -> list[Requirement]:
    """
    Return versioned requirements from a pyproject.toml that belong to internal_packages.

    Normalises package names (hyphens and underscores are treated as equivalent) before
    comparing, so "flamapy-fw" and "flamapy_fw" are considered the same package.

    Args:
        pyproject_file: Path to the pyproject.toml file.
        internal_packages: Set of package names to keep (e.g. {"flamapy-fw", "flamapy-fm"}).

    Returns:
        List of Requirement objects whose names are in internal_packages.
    """

    def _normalize(name: str) -> str:
        return name.lower().replace("_", "-")

    normalized = {_normalize(p) for p in internal_packages}
    return [r for r in _parse_pyproject_requirements(pyproject_file)
            if _normalize(r.name) in normalized]


def wait_for_internal_requirements(
    pyproject_file: str,
    internal_packages: set[str],
    check_interval: int = 10,
) -> list[str]:
    """
    Block until all internal versioned dependencies in a pyproject.toml are on PyPI.

    Unlike wait_for_pyproject_requirements, this function ignores build-system
    dependencies (e.g. setuptools) and third-party runtime dependencies, waiting
    only for packages whose names appear in internal_packages.  This is the correct
    behaviour during a coordinated multi-repo release where each package is published
    to PyPI by CI only after its git tag is pushed.

    Args:
        pyproject_file: Path to the pyproject.toml file.
        internal_packages: Set of package names to wait for.
        check_interval: Seconds to wait between PyPI checks (default: 10).

    Returns:
        List of package names (as declared in the file) that were waited for.
        An empty list means there was nothing internal to wait for.
    """
    reqs = get_internal_requirements(pyproject_file, internal_packages)
    if not reqs:
        return []
    while True:
        if all(_package_available(r) for r in reqs):
            return [str(r) for r in reqs]
        time.sleep(check_interval)
