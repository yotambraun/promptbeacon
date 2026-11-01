"""Scan open-source projects and packages by reference.

Sources: GitHub, PyPI, npm, crates.io and the Hugging Face Hub.

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
    CratesSource,
    GitHubSource,
    HttpResponse,
    HuggingFaceSource,
    MetadataCache,
    MetadataSource,
    NpmSource,
    ProjectMetadata,
    ProjectMetadataError,
    ProjectMetadataUnavailable,
    PyPISource,
    available_sources,
    fetch_project,
    parse_project_ref,
    project_name_from_ref,
    register_source,
)

__all__ = [
    "CategoryGuess",
    "CratesSource",
    "GitHubSource",
    "HttpResponse",
    "HuggingFaceSource",
    "MetadataCache",
    "MetadataSource",
    "NpmSource",
    "ProjectMetadata",
    "ProjectMetadataError",
    "ProjectMetadataUnavailable",
    "ProjectProfile",
    "PyPISource",
    "available_sources",
    "fetch_project",
    "guess_category",
    "guess_competitors",
    "parse_project_ref",
    "project_name_from_ref",
    "profile_project",
    "register_source",
]
