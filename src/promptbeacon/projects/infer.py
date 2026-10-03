"""Offline guesses of a project's category and likely competitors.

These are deliberately simple, transparent heuristics over public metadata
(description, topics/keywords, README). They never call a model; when an LLM
key is available, ``--infer-category`` / ``with_category_inference()`` can
refine the guess with one call. Every guess carries a ``basis`` string so the
CLI can show where it came from, and users can override it with
``--category`` / ``--competitor``.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from promptbeacon.projects.sources import ProjectMetadata

Confidence = Literal["high", "medium", "low"]

# Nouns that name a kind of software; a category usually ends in one.
_KIND_NOUNS = {
    "client", "server", "framework", "library", "toolkit", "sdk", "cli", "orm",
    "database", "db", "engine", "parser", "linter", "formatter", "compiler",
    "bundler", "runtime", "router", "scheduler", "queue", "cache", "proxy",
    "editor", "ide", "generator", "manager", "platform", "service", "api",
    "plugin", "extension", "driver", "wrapper", "interface", "tool", "app",
    "application", "dashboard", "monitor", "tracker", "store", "validator",
    "renderer", "emulator", "simulator", "visualizer", "debugger", "profiler",
    "translator", "converter", "downloader", "scraper", "crawler", "bot",
    "agent", "model", "dataset", "benchmark", "theme", "font", "component",
    "components", "system", "browser", "terminal", "shell", "language",
}  # fmt: skip

# Topics/keywords too broad to describe a category on their own.
_GENERIC = {
    "python", "python3", "python2", "javascript", "typescript", "js", "ts", "node",
    "nodejs", "node-js", "rust", "go", "golang", "java", "kotlin", "swift", "ruby",
    "php", "c", "cpp", "c++", "csharp", "dotnet", "scala", "elixir", "haskell",
    "library", "lib", "package", "module", "open-source", "opensource", "oss",
    "hacktoberfest", "awesome", "mit", "apache", "free", "tool", "tools", "app",
    "utility", "utilities", "util", "utils", "software", "project", "code",
    "developer", "developers", "dev", "github", "pypi", "npm",
} | {f"python{v}" for v in range(2, 4)}  # fmt: skip

# Leading words that describe quality, not category (English descriptions).
_FILLER = {
    "a", "an", "the", "fast", "faster", "fastest", "simple", "simpler", "modern",
    "lightweight", "light", "minimal", "minimalist", "unopinionated", "powerful",
    "elegant", "beautiful", "tiny", "small", "smart", "easy", "easiest", "friendly",
    "robust", "blazing", "blazingly", "high", "performance", "high-performance",
    "next", "generation", "next-generation", "new", "best", "official", "open",
    "source", "open-source", "free", "awesome", "flexible", "extensible",
    "production-ready", "batteries-included", "full-featured", "feature-rich",
    "zero-dependency", "dependency-free", "secure", "reliable", "scalable",
    "efficient", "pure", "native", "complete", "comprehensive", "ultimate",
    "yet", "another", "your", "my", "our", "very", "super", "really",
}  # fmt: skip

_PREPOSITIONS = {
    "for", "with", "in", "to", "that", "which", "on", "of", "using", "built",
    "written", "made", "designed", "based", "from", "by", "and", "&",
}  # fmt: skip

_LANGUAGE_LABEL = {
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Python": "python",
    "Go": "go",
    "Rust": "rust",
    "Java": "java",
    "Kotlin": "kotlin",
    "Ruby": "ruby",
    "PHP": "php",
    "C#": "c#",
    "C++": "c++",
    "Swift": "swift",
    "Elixir": "elixir",
    "Scala": "scala",
    "Dart": "dart",
}


@dataclass
class CategoryGuess:
    """A best-effort category with how sure we are and why."""

    category: str | None
    confidence: Confidence
    basis: str


@dataclass
class ProjectProfile:
    """Brand, category and competitor candidates for a project scan."""

    metadata: ProjectMetadata
    category: CategoryGuess
    competitors: list[str] = field(default_factory=list)
    competitor_basis: str = ""


def _words(text: str) -> list[str]:
    return re.findall(r"[\w][\w+#.\-]*", text.lower())


def _mostly_latin(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) > 0.8


def _brand_tokens(meta: ProjectMetadata) -> set[str]:
    names = [meta.name, *meta.aliases, meta.ref.split("/")[-1]]
    tokens: set[str] = set()
    for n in names:
        low = n.lower()
        tokens.add(low)
        tokens.update(re.split(r"[-_.\s/]+", low))
    return {t for t in tokens if t}


def _description_phrase(meta: ProjectMetadata, brand: set[str]) -> str | None:
    """The noun phrase a description leads with, minus brand and filler words."""
    desc = meta.description.strip()
    if not desc or not _mostly_latin(desc):
        return None
    clauses = re.split(r"[.;:!?()\[\]—–]|\s-\s", desc)
    segments = [seg for clause in clauses for seg in clause.split(",")]
    for segment in segments:
        words = [w for w in _words(segment) if w not in brand]
        while words and words[0] in _FILLER:
            words.pop(0)
        head: list[str] = []
        for w in words:
            if w in _PREPOSITIONS:
                break
            if w not in _FILLER:
                head.append(w)
        if head:
            return " ".join(head[-4:])
    return None


def _topic_phrases(meta: ProjectMetadata, brand: set[str]) -> list[str]:
    phrases = []
    for kw in meta.keywords:
        low = kw.lower().strip()
        if not low or low in _GENERIC or low in brand:
            continue
        phrases.append(re.sub(r"[-_]+", " ", low))
    return phrases


def _with_language(phrase: str, meta: ProjectMetadata) -> str:
    label = _LANGUAGE_LABEL.get(meta.language or "")
    if label and label not in phrase.split():
        return f"{label} {phrase}"
    return phrase


def guess_category(meta: ProjectMetadata) -> CategoryGuess:
    """Guess a buyer-style category ("python http client") from metadata."""
    brand = _brand_tokens(meta)
    desc_words = set(_words(meta.description))
    topics = _topic_phrases(meta, brand)
    phrase = _description_phrase(meta, brand)

    if phrase:
        last = phrase.split()[-1]
        if len(phrase.split()) >= 2 and last in _KIND_NOUNS:
            return CategoryGuess(_with_language(phrase, meta), "high", "description")
        if last in _KIND_NOUNS:
            # A bare kind ("framework"): qualify it with the most relevant topic.
            ranked = sorted(topics, key=lambda t: t not in desc_words)
            for t in ranked:
                if t != last and " " not in t:
                    return CategoryGuess(
                        _with_language(f"{t} {last}", meta),
                        "medium",
                        f"description + topic '{t}'",
                    )
            return CategoryGuess(_with_language(phrase, meta), "low", "description")

    multiword = [t for t in topics if " " in t and t.split()[-1] in _KIND_NOUNS]
    if multiword:
        best = max(multiword, key=lambda t: len(set(t.split()) & desc_words))
        return CategoryGuess(_with_language(best, meta), "medium", f"topic '{best}'")

    nouns = [t for t in topics if t in _KIND_NOUNS]
    modifiers = [t for t in topics if t not in _KIND_NOUNS and " " not in t]
    if nouns and modifiers:
        cat = f"{modifiers[0]} {nouns[0]}"
        return CategoryGuess(_with_language(cat, meta), "medium", "topics")

    if phrase:
        return CategoryGuess(_with_language(phrase, meta), "low", "description")
    if topics:
        return CategoryGuess(_with_language(topics[0], meta), "low", "topics")
    return CategoryGuess(None, "low", "no description or topics")


# Phrases that introduce a peer project in READMEs. English-only by nature;
# READMEs in other languages simply yield no candidates (use --competitor or
# the optional LLM inference instead).
_PEER_PATTERNS = [
    r"(?:alternatives?\s+to|instead\s+of|compared\s+(?:to|with)|vs\.?|versus|"
    r"inspired\s+by|similar\s+to|(?:drop-in\s+)?replacement\s+for|"
    r"compatible\s+with|port\s+of|fork\s+of)\s+(?:the\s+)?\[?`?([A-Za-z][\w.+\-]{1,40})",
    r"`?([A-Za-z][\w.+\-]{1,40})`?-compatible",
]
_PEER_STOP = {
    "the", "a", "an", "other", "others", "your", "existing", "many", "most", "it",
    "this", "that", "these", "those", "them", "any", "all", "some", "standard",
    "traditional", "popular", "similar", "previous", "older", "legacy", "native",
    "python", "javascript", "typescript", "node", "rust", "go", "java", "http",
    "api", "apis", "json", "sql", "html", "css", "using", "use", "and", "or",
}  # fmt: skip


def guess_competitors(meta: ProjectMetadata, limit: int = 4) -> list[str]:
    """Peer projects a README compares itself to (best effort, may be empty)."""
    if not meta.readme:
        return []
    brand = _brand_tokens(meta)
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    for pattern in _PEER_PATTERNS:
        for match in re.finditer(pattern, meta.readme, re.IGNORECASE):
            name = match.group(1).strip(".-`")
            low = name.lower()
            if len(low) < 2 or low in _PEER_STOP or low in brand:
                continue
            counts[low] += 1
            display.setdefault(low, name)
    return [display[n] for n, _ in counts.most_common(limit)]


def profile_project(meta: ProjectMetadata) -> ProjectProfile:
    """Category guess plus competitor candidates for a project."""
    competitors = guess_competitors(meta)
    return ProjectProfile(
        metadata=meta,
        category=guess_category(meta),
        competitors=competitors,
        competitor_basis="README mentions" if competitors else "",
    )
