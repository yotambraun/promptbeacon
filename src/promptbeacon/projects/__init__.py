"""Scan open-source projects and packages by reference (GitHub, PyPI, npm).

``fetch_project("pypi:httpx")`` reads public metadata; ``profile_project``
guesses a category and competitor candidates offline; ``Beacon.from_project``
turns that into a ready-to-scan :class:`~promptbeacon.Beacon`.
"""

from promptbeacon.projects.infer import (
    CategoryGuess,
    ProjectProfile,
    guess_category,
    guess_competitors,
    profile_project,
)
from promptbeacon.projects.sources import (
    GitHubSource,
    HttpResponse,
    MetadataCache,
    MetadataSource,
    NpmSource,
    ProjectMetadata,
    ProjectMetadataError,
    PyPISource,
    available_sources,
    fetch_project,
    parse_project_ref,
    register_source,
)

__all__ = [
    "CategoryGuess",
    "GitHubSource",
    "HttpResponse",
    "MetadataCache",
    "MetadataSource",
    "NpmSource",
    "ProjectMetadata",
    "ProjectMetadataError",
    "ProjectProfile",
    "PyPISource",
    "available_sources",
    "fetch_project",
    "guess_category",
    "guess_competitors",
    "parse_project_ref",
    "profile_project",
    "register_source",
]
