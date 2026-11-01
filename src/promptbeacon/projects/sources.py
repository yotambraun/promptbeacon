"""Public project metadata sources (GitHub, PyPI, npm, crates.io, Hugging Face).

Each source is one small class that turns a reference (``owner/name``, a
package name) into :class:`ProjectMetadata`. Add a source by subclassing
:class:`MetadataSource` and calling :func:`register_source`; the CLI
(``--project kind:ref``), the Python API (``Beacon.from_project``) and the MCP
server pick it up automatically.

Network access goes through an injectable ``http`` callable (tests pass a fake),
responses are cached on disk for a day, a ``User-Agent`` is always sent, and
``GITHUB_TOKEN``/``GH_TOKEN`` is used when set (the unauthenticated GitHub API
allows 60 requests per hour).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import quote

from promptbeacon.core.exceptions import PromptBeaconError

README_LIMIT = 20_000


class ProjectMetadataError(PromptBeaconError):
    """Project metadata could not be fetched (not found, rate limited, offline)."""


class ProjectMetadataUnavailable(ProjectMetadataError):
    """The registry could not be reached (offline, DNS, timeout).

    Distinct from "not found" so keyless demo runs can carry on offline.
    """


@dataclass
class HttpResponse:
    """Minimal HTTP response used by metadata sources."""

    status: int
    text: str
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        return json.loads(self.text)


HttpGet = Callable[[str, dict[str, str]], HttpResponse]


def default_http_get(url: str, headers: dict[str, str]) -> HttpResponse:
    """GET with httpx (a core dependency), following redirects."""
    import httpx

    try:
        resp = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
    except httpx.HTTPError as e:
        raise ProjectMetadataUnavailable(f"Could not reach {url}: {e}") from e
    return HttpResponse(
        resp.status_code, resp.text, {k.lower(): v for k, v in resp.headers.items()}
    )


@dataclass
class ProjectMetadata:
    """What a public registry says about a project."""

    source: str
    ref: str
    name: str
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    language: str | None = None
    homepage: str | None = None
    url: str | None = None
    readme: str = ""
    aliases: list[str] = field(default_factory=list)
    # A category the registry states outright (e.g. a Hugging Face model's
    # pipeline_tag), with where it came from. Preferred over the guess from
    # the description; ``--category`` still wins.
    category_hint: str | None = None
    category_hint_basis: str = ""

    def hints(self) -> list[str]:
        """Short context for an optional LLM category inference."""
        parts = [f"{self.source} project {self.ref}"]
        if self.description:
            parts.append(f"description: {self.description}")
        if self.keywords:
            parts.append("keywords: " + ", ".join(self.keywords[:15]))
        if self.language:
            parts.append(f"language: {self.language}")
        return parts


class MetadataCache:
    """Tiny on-disk cache for successful metadata responses."""

    def __init__(self, directory: Path | None = None, ttl_seconds: int = 86_400):
        if directory is None:
            from promptbeacon.core.config import get_promptbeacon_home

            directory = get_promptbeacon_home() / "cache" / "projects"
        self.directory = directory
        self.ttl = ttl_seconds

    def _path(self, url: str) -> Path:
        return self.directory / (hashlib.sha256(url.encode()).hexdigest() + ".json")

    def get(self, url: str) -> str | None:
        path = self._path(url)
        try:
            if time.time() - path.stat().st_mtime > self.ttl:
                return None
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def set(self, url: str, text: str) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._path(url).write_text(text, encoding="utf-8")
        except OSError:
            pass  # caching is best-effort


class MetadataSource:
    """Base class: fetch one kind of project reference."""

    kind: ClassVar[str]
    label: ClassVar[str]
    example: ClassVar[str]

    def __init__(
        self, http: HttpGet | None = None, cache: MetadataCache | None = None
    ) -> None:
        self._http = http or default_http_get
        self._cache = cache

    def normalize(self, ref: str) -> str:
        ref = ref.strip()
        if not ref:
            raise ProjectMetadataError(f"Empty {self.label} reference")
        return ref

    def fetch(self, ref: str) -> ProjectMetadata:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- helpers ----------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        from promptbeacon import __version__

        return {
            "User-Agent": f"promptbeacon/{__version__} (+https://github.com/yotambraun/promptbeacon)",
            "Accept": "application/json",
        }

    def _get(self, url: str, headers: dict[str, str] | None = None) -> HttpResponse:
        if self._cache is not None:
            cached = self._cache.get(url)
            if cached is not None:
                return HttpResponse(200, cached)
        resp = self._http(url, {**self._headers(), **(headers or {})})
        if resp.status == 200 and self._cache is not None:
            self._cache.set(url, resp.text)
        return resp

    def _error(self, resp: HttpResponse, what: str) -> ProjectMetadataError:
        if resp.status == 404:
            return ProjectMetadataError(f"{self.label}: {what} was not found.")
        if resp.status in (403, 429):
            return ProjectMetadataError(
                f"{self.label} rate limit or access denied for {what} "
                f"(HTTP {resp.status}). Try again later."
            )
        return ProjectMetadataError(
            f"{self.label} returned HTTP {resp.status} for {what}."
        )


class GitHubSource(MetadataSource):
    """``owner/name`` (or a github.com URL) via the GitHub REST API."""

    kind = "github"
    label = "GitHub"
    example = "encode/httpx"
    api = "https://api.github.com"

    def normalize(self, ref: str) -> str:
        ref = super().normalize(ref)
        ref = re.sub(r"^(https?://)?(www\.)?github\.com/", "", ref).strip("/")
        ref = re.sub(r"\.git$", "", ref)
        parts = ref.split("/")
        if len(parts) < 2 or not all(parts[:2]):
            raise ProjectMetadataError(
                f"GitHub repositories look like owner/name, got {ref!r}"
            )
        return "/".join(parts[:2])

    def _headers(self) -> dict[str, str]:
        headers = {**super()._headers(), "Accept": "application/vnd.github+json"}
        token = (
            os.environ.get("GITHUB_TOKEN", "").strip()
            or os.environ.get("GH_TOKEN", "").strip()
        )
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _error(self, resp: HttpResponse, what: str) -> ProjectMetadataError:
        if resp.status in (403, 429) and (
            resp.headers.get("x-ratelimit-remaining") == "0" or resp.status == 429
        ):
            reset = resp.headers.get("x-ratelimit-reset")
            when = ""
            if reset and reset.isdigit():
                minutes = max(0, round((int(reset) - time.time()) / 60))
                when = f" It resets in about {minutes} min."
            return ProjectMetadataError(
                "GitHub API rate limit reached (60 requests/hour without a token)."
                f"{when} Set GITHUB_TOKEN to raise the limit."
            )
        return super()._error(resp, what)

    def fetch(self, ref: str) -> ProjectMetadata:
        ref = self.normalize(ref)
        resp = self._get(f"{self.api}/repos/{ref}")
        if resp.status != 200:
            raise self._error(resp, f"repository {ref}")
        data = resp.json()
        readme = ""
        readme_resp = self._get(
            f"{self.api}/repos/{ref}/readme",
            {"Accept": "application/vnd.github.raw+json"},
        )
        if readme_resp.status == 200:
            readme = readme_resp.text[:README_LIMIT]
        name = data.get("name") or ref.split("/")[1]
        return ProjectMetadata(
            source=self.kind,
            ref=data.get("full_name") or ref,
            name=name,
            description=data.get("description") or "",
            keywords=list(data.get("topics") or []),
            language=data.get("language"),
            homepage=data.get("homepage") or None,
            url=data.get("html_url") or f"https://github.com/{ref}",
            readme=readme,
            aliases=[data.get("full_name") or ref],
        )


class PyPISource(MetadataSource):
    """A Python package name via the PyPI JSON API."""

    kind = "pypi"
    label = "PyPI"
    example = "httpx"

    def normalize(self, ref: str) -> str:
        ref = super().normalize(ref)
        ref = re.sub(r"^(https?://)?pypi\.org/project/", "", ref).strip("/")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", ref):
            raise ProjectMetadataError(f"Not a valid PyPI package name: {ref!r}")
        return ref

    def fetch(self, ref: str) -> ProjectMetadata:
        ref = self.normalize(ref)
        resp = self._get(f"https://pypi.org/pypi/{quote(ref)}/json")
        if resp.status != 200:
            raise self._error(resp, f"package {ref}")
        info = resp.json().get("info") or {}
        keywords = [
            k.strip()
            for k in re.split(r"[,\s]+", info.get("keywords") or "")
            if k.strip()
        ]
        topics = [
            c.split("::")[-1].strip()
            for c in info.get("classifiers") or []
            if c.startswith("Topic ::")
        ]
        urls = info.get("project_urls") or {}
        source_url = next(
            (
                v
                for k, v in urls.items()
                if k.lower() in ("source", "repository", "code")
            ),
            None,
        )
        name = info.get("name") or ref
        return ProjectMetadata(
            source=self.kind,
            ref=ref,
            name=name,
            description=info.get("summary") or "",
            keywords=keywords + topics,
            language="Python",
            homepage=info.get("home_page") or urls.get("Homepage") or None,
            url=source_url or f"https://pypi.org/project/{name}/",
            readme=(info.get("description") or "")[:README_LIMIT],
            aliases=[ref] if ref != name else [],
        )


class NpmSource(MetadataSource):
    """A JavaScript package name (scoped names allowed) via the npm registry."""

    kind = "npm"
    label = "npm"
    example = "express"

    def normalize(self, ref: str) -> str:
        ref = super().normalize(ref)
        ref = re.sub(r"^(https?://)?(www\.)?npmjs\.com/package/", "", ref).strip("/")
        if not re.fullmatch(r"(@[a-z0-9~][\w.~-]*/)?[a-z0-9~][\w.~-]*", ref, re.I):
            raise ProjectMetadataError(f"Not a valid npm package name: {ref!r}")
        return ref

    def fetch(self, ref: str) -> ProjectMetadata:
        ref = self.normalize(ref)
        resp = self._get(f"https://registry.npmjs.org/{quote(ref, safe='@')}/latest")
        if resp.status != 200:
            raise self._error(resp, f"package {ref}")
        data = resp.json()
        repo = data.get("repository")
        repo_url = repo.get("url") if isinstance(repo, dict) else repo
        if isinstance(repo_url, str):
            repo_url = re.sub(r"^git\+|\.git$", "", repo_url)
        keywords = data.get("keywords") or []
        name = data.get("name") or ref
        language = (
            "TypeScript" if data.get("types") or data.get("typings") else "JavaScript"
        )
        return ProjectMetadata(
            source=self.kind,
            ref=ref,
            name=name.split("/")[-1] if name.startswith("@") else name,
            description=data.get("description") or "",
            keywords=[str(k) for k in keywords if isinstance(k, str)],
            language=language,
            homepage=data.get("homepage") or None,
            url=repo_url or f"https://www.npmjs.com/package/{name}",
            readme=(data.get("readme") or "")[:README_LIMIT],
            aliases=[name] if name.startswith("@") else [],
        )


def _strip_html(html: str) -> str:
    """Rough HTML to text (READMEs rendered by a registry), for peer guessing."""
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return re.sub(r"[ \t]+", " ", text)


def _first_paragraph(markdown: str, limit: int = 240) -> str:
    """The first prose paragraph of a Markdown README (front matter skipped)."""
    text = re.sub(r"(?s)\A---\n.*?\n---\n", "", markdown.lstrip("\ufeff"))
    for block in re.split(r"\n\s*\n", text):
        # Drop heading lines ("# name") that sit directly above the prose.
        block = "\n".join(
            line for line in block.splitlines() if not line.lstrip().startswith("#")
        ).strip()
        if not block or block.startswith(("#", "<", "!", "[!", "```", "|", ">", "-")):
            continue
        block = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", block)  # links
        block = re.sub(r"[*_`]+", "", " ".join(block.split()))
        if len(block) > limit:
            block = block[:limit].rsplit(" ", 1)[0] + "..."
        return block
    return ""


class CratesSource(MetadataSource):
    """A Rust crate via the crates.io API (``/api/v1/crates/<name>``)."""

    kind = "crates"
    label = "crates.io"
    example = "serde"
    api = "https://crates.io/api/v1"

    def normalize(self, ref: str) -> str:
        ref = super().normalize(ref)
        ref = re.sub(r"^(https?://)?(www\.)?crates\.io/crates/", "", ref).strip("/")
        ref = ref.split("/")[0]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", ref):
            raise ProjectMetadataError(f"Not a valid crate name: {ref!r}")
        return ref

    def fetch(self, ref: str) -> ProjectMetadata:
        ref = self.normalize(ref)
        # include= skips the (very long) version list.
        resp = self._get(f"{self.api}/crates/{quote(ref)}?include=keywords,categories")
        if resp.status != 200:
            raise self._error(resp, f"crate {ref}")
        data = resp.json()
        crate = data.get("crate") or {}
        name = crate.get("name") or ref
        keywords = [str(k) for k in crate.get("keywords") or [] if k]
        # Category slugs such as "web-programming::http-client" -> "http-client".
        slugs = [str(c) for c in crate.get("categories") or [] if c]
        topics = [s.split("::")[-1] for s in slugs if not s.startswith("no-std")]
        version = crate.get("max_stable_version") or crate.get("max_version")
        readme = ""
        if version:
            # Redirects to the rendered README on static.crates.io; optional.
            readme_resp = self._get(
                f"{self.api}/crates/{quote(name)}/{quote(str(version))}/readme",
                {"Accept": "text/html"},
            )
            if readme_resp.status == 200:
                readme = _strip_html(readme_resp.text)[:README_LIMIT]
        return ProjectMetadata(
            source=self.kind,
            ref=name,
            name=name,
            description=(crate.get("description") or "").strip(),
            keywords=keywords + [t for t in topics if t not in keywords],
            language="Rust",
            homepage=crate.get("homepage") or None,
            url=crate.get("repository") or f"https://crates.io/crates/{name}",
            readme=readme,
        )


# What people call a model with a given Hugging Face pipeline_tag. Anything
# else becomes "<pipeline tag words> model" ("image classification model").
_HF_PIPELINE_CATEGORY = {
    "text-generation": "open-weight language model",
    "feature-extraction": "text embedding model",
    "sentence-similarity": "text embedding model",
    "automatic-speech-recognition": "speech recognition model",
    "text-to-speech": "text-to-speech model",
    "text-to-image": "text-to-image model",
    "image-text-to-text": "vision language model",
}
_HF_KINDS = {"models": "model", "datasets": "dataset", "spaces": "space"}


class HuggingFaceSource(MetadataSource):
    """A Hugging Face Hub model, dataset or Space via the Hub API.

    References: ``owner/name`` (a model), ``datasets/owner/name``,
    ``spaces/owner/name``, or a huggingface.co URL.
    """

    kind = "hf"
    label = "Hugging Face"
    example = "sentence-transformers/all-MiniLM-L6-v2"
    hub = "https://huggingface.co"

    def split(self, ref: str) -> tuple[str, str]:
        """``(repo_type, owner/name)``; repo_type is models, datasets or spaces."""
        ref = super().normalize(ref)
        ref = re.sub(r"^(https?://)?(www\.)?(hf\.co|huggingface\.co)/", "", ref)
        ref = ref.strip("/")
        parts = ref.split("/")
        repo_type = "models"
        if parts and parts[0] in _HF_KINDS:
            repo_type = parts.pop(0)
        if len(parts) < 2 or not all(re.fullmatch(r"[\w.-]+", p) for p in parts[:2]):
            raise ProjectMetadataError(
                "Hugging Face references look like owner/name (a model), "
                f"datasets/owner/name or spaces/owner/name, got {ref!r}"
            )
        return repo_type, "/".join(parts[:2])

    def normalize(self, ref: str) -> str:
        repo_type, repo_id = self.split(ref)
        return repo_id if repo_type == "models" else f"{repo_type}/{repo_id}"

    def fetch(self, ref: str) -> ProjectMetadata:
        repo_type, repo_id = self.split(ref)
        kind = _HF_KINDS[repo_type]
        resp = self._get(f"{self.hub}/api/{repo_type}/{repo_id}")
        if resp.status in (401, 403) and "gated" not in resp.text.lower():
            raise ProjectMetadataError(
                f"Hugging Face: {kind} {repo_id} is private or was not found."
            )
        if resp.status != 200:
            raise self._error(resp, f"{kind} {repo_id}")
        data = resp.json()
        card = data.get("cardData") or {}
        tags = [str(t) for t in data.get("tags") or []]
        prefix = "" if repo_type == "models" else f"{repo_type}/"
        readme = ""
        readme_resp = self._get(
            f"{self.hub}/{prefix}{repo_id}/raw/main/README.md", {"Accept": "text/plain"}
        )
        if readme_resp.status == 200:
            readme = readme_resp.text[:README_LIMIT]

        hint: str | None = None
        hint_basis = ""
        keywords = [t for t in tags if ":" not in t]
        if kind == "model":
            pipeline = data.get("pipeline_tag") or card.get("pipeline_tag")
            if pipeline:
                hint = _HF_PIPELINE_CATEGORY.get(
                    pipeline, pipeline.replace("-", " ") + " model"
                )
                hint_basis = f"Hugging Face pipeline_tag '{pipeline}'"
        elif kind == "dataset":
            tasks = list(card.get("task_categories") or []) or [
                t.split(":", 1)[1] for t in tags if t.startswith("task_categories:")
            ]
            if tasks:
                hint = f"{str(tasks[0]).replace('-', ' ')} dataset"
                hint_basis = f"Hugging Face task_categories '{tasks[0]}'"
            keywords += [str(t).replace("-", " ") for t in tasks]

        description = (
            str(card.get("short_description") or "").strip()
            or _first_paragraph(readme)
            or " ".join(str(data.get("description") or "").split())[:240]
        )
        name = repo_id.split("/")[-1]
        title = str(card.get("pretty_name") or card.get("title") or "").strip()
        aliases = [repo_id] + ([title] if title and title != name else [])
        return ProjectMetadata(
            source=self.kind,
            ref=f"{prefix}{repo_id}",
            name=name,
            description=description,
            keywords=keywords,
            language=None,
            url=f"{self.hub}/{prefix}{repo_id}",
            readme=readme,
            aliases=aliases,
            category_hint=hint,
            category_hint_basis=hint_basis,
        )


_SOURCES: dict[str, type[MetadataSource]] = {}


def register_source(source: type[MetadataSource]) -> type[MetadataSource]:
    """Register a metadata source class under its ``kind`` (usable as a decorator)."""
    _SOURCES[source.kind] = source
    return source


for _cls in (GitHubSource, PyPISource, NpmSource, CratesSource, HuggingFaceSource):
    register_source(_cls)


_KIND_ALIASES = {"crate": "crates", "huggingface": "hf"}


def available_sources() -> list[str]:
    """Registered source kinds, e.g. ``["crates", "github", "hf", "npm", "pypi"]``."""
    return sorted(_SOURCES)


def parse_project_ref(ref: str) -> tuple[str, str]:
    """Split ``"kind:ref"`` (e.g. ``"pypi:httpx"``) into ``(kind, ref)``.

    ``crate:`` and ``huggingface:`` are accepted for ``crates:`` and ``hf:``.
    crates.io and huggingface.co URLs are recognised; a bare github.com URL or
    ``owner/name`` is treated as GitHub.
    """
    ref = ref.strip()
    kind, sep, rest = ref.partition(":")
    kind = _KIND_ALIASES.get(kind.lower(), kind.lower())
    if sep and kind in _SOURCES and not rest.startswith("//"):
        return kind, rest
    if re.search(r"(^|//|\.)crates\.io/crates/", ref):
        return "crates", ref
    if re.search(r"(^|//|\.)(huggingface|hf)\.co/", ref):
        return "hf", ref
    if "github.com/" in ref or re.fullmatch(r"[\w.-]+/[\w.-]+", ref):
        return "github", ref
    raise ProjectMetadataError(
        f"Unknown project reference {ref!r}. Use one of: "
        + ", ".join(f"{k}:{_SOURCES[k].example}" for k in available_sources())
    )


def project_name_from_ref(ref: str) -> str:
    """The project name a reference points at, without any network access.

    ``"crates:serde"`` -> ``"serde"``, ``"github:encode/httpx"`` -> ``"httpx"``.
    """
    kind, rest = parse_project_ref(ref)
    source = _SOURCES[kind]()
    return source.normalize(rest).rstrip("/").split("/")[-1]


def fetch_project(
    ref: str,
    kind: str | None = None,
    *,
    http: HttpGet | None = None,
    cache: MetadataCache | None | bool = True,
) -> ProjectMetadata:
    """Fetch public metadata for a project.

    Args:
        ref: ``"kind:ref"`` (``"pypi:httpx"``), or a bare ref with ``kind``.
        kind: Source kind (``"github"``, ``"pypi"``, ``"npm"``, ``"crates"``,
            ``"hf"``, or registered).
        http: Optional HTTP getter (for tests or custom transports).
        cache: ``True`` for the default on-disk cache, ``False``/``None`` to
            disable, or a :class:`MetadataCache`.

    Raises:
        ProjectMetadataError: Unknown source, not found, rate limited, offline.
    """
    if kind is None:
        kind, ref = parse_project_ref(ref)
    source_cls = _SOURCES.get(kind.lower())
    if source_cls is None:
        raise ProjectMetadataError(
            f"Unknown project source {kind!r}. Available: {', '.join(available_sources())}"
        )
    cache_obj = MetadataCache() if cache is True else (cache or None)
    try:
        return source_cls(http=http, cache=cache_obj).fetch(ref)
    except (ValueError, KeyError, TypeError) as e:
        raise ProjectMetadataError(
            f"Unexpected {source_cls.label} response: {e}"
        ) from e
