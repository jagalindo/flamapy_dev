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


def _normalize_project_name(name: str) -> str:
    """Normalise a project name for use in a simple-index URL (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _available_versions(req: Requirement) -> set[str]:
    """
    Return the versions of a package published on PyPI's simple index.

    The simple index is the same source pip (and therefore CI) resolves against,
    so it is the authoritative answer to "can this version be installed yet?".
    The JSON metadata API (``/pypi/<name>/json``) can report a release before it
    has propagated to the simple index, which is the race this avoids.

    Versions are read from the PEP 700 ``versions`` field when present, otherwise
    derived from the ``files`` filenames in the PEP 691 JSON simple response.

    Args:
        req: A Requirement object specifying the package.

    Returns:
        The set of version strings available, or an empty set on any error.
    """
    url = f"https://pypi.org/simple/{_normalize_project_name(req.name)}/"
    headers = {"Accept": "application/vnd.pypi.simple.v1+json"}
    try:
        with request.urlopen(
            request.Request(url, headers=headers), timeout=10, context=_SSL_CONTEXT
        ) as resp:
            if resp.status != HTTP_OK:
                return set()
            data = json.load(resp)
    except (error.URLError, json.JSONDecodeError, OSError):
        return set()

    versions = data.get("versions")
    if versions:
        return set(versions)

    # Fall back to parsing versions out of the distribution filenames.
    found: set[str] = set()
    name_prefix = _normalize_project_name(req.name).replace("-", "_")
    for file_entry in data.get("files", []):
        filename = file_entry.get("filename", "")
        if filename.endswith(".whl"):
            parts = filename[:-4].split("-")
            if len(parts) >= 2:
                found.add(parts[1])
        elif filename.endswith(".tar.gz"):
            stem = filename[: -len(".tar.gz")]
            if stem.lower().startswith(name_prefix + "-"):
                found.add(stem[len(name_prefix) + 1:])
    return found


def _package_available(req: Requirement) -> bool:
    """
    Check if a package version is available on PyPI's simple index.

    Args:
        req: A Requirement object specifying the package and version constraints.

    Returns:
        True if a matching version is available on the simple index, else False.
    """
    versions = _available_versions(req)
    if not versions:
        return False
    if not req.specifier:
        return True
    for ver in versions:
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
