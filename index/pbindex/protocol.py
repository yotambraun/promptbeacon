"""Pinned category protocols (``index/categories/<id>.json``)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from promptbeacon.core.config import Provider

INDEX_DIR = Path(__file__).resolve().parents[1]
CATEGORIES_DIR = INDEX_DIR / "categories"
MIN_CANDIDATES = 3
SCHEMA_VERSION = 1


class Candidate(BaseModel):
    """A project that can be ranked in a category."""

    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    match: list[str] = Field(
        default_factory=list,
        description="Terms that count as a mention (default: the name). Use them "
        "for names that are also common words.",
    )
    case_sensitive: bool = False

    @property
    def terms(self) -> list[str]:
        return list(self.match) or [self.name]

    def pattern(self) -> re.Pattern[str]:
        """Whole-word match of any term (not inside a longer word or hyphenation)."""
        alternatives = "|".join(
            re.escape(t) for t in sorted(self.terms, key=len, reverse=True)
        )
        flags = 0 if self.case_sensitive else re.IGNORECASE
        return re.compile(rf"(?<![\w-])(?:{alternatives})(?![\w-])", flags)


class IndexProtocol(BaseModel):
    """Everything that is fixed for one category: prompts, models, runs."""

    schema_version: int = Field(SCHEMA_VERSION, alias="schema")
    id: str = Field(..., pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    category: str = Field(..., min_length=3)
    group: str = "Other"
    candidates: list[Candidate]
    prompts: list[str] = Field(..., min_length=1)
    providers: dict[str, str] = Field(..., min_length=1)
    runs: int = Field(3, ge=1, le=20)
    tier: Literal["base_model"] = "base_model"
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(1024, ge=64, le=8192)

    model_config = {"populate_by_name": True}

    @field_validator("providers")
    @classmethod
    def _known_providers(cls, value: dict[str, str]) -> dict[str, str]:
        for name, model in value.items():
            Provider.parse(name)
            if not model.strip():
                raise ValueError(f"empty model for provider {name!r}")
        return value

    @model_validator(mode="after")
    def _fair_candidates(self) -> IndexProtocol:
        names = [c.name for c in self.candidates]
        if len(names) < MIN_CANDIDATES:
            raise ValueError(
                f"{self.id}: at least {MIN_CANDIDATES} candidates are needed"
            )
        if len({n.lower() for n in names}) != len(names):
            raise ValueError(f"{self.id}: duplicate candidate names")
        # Never pre-ranked: candidates are listed alphabetically.
        if names != sorted(names, key=str.lower):
            raise ValueError(f"{self.id}: candidates must be in alphabetical order")
        if len(set(self.prompts)) != len(self.prompts):
            raise ValueError(f"{self.id}: duplicate prompts")
        return self

    @property
    def provider_models(self) -> list[tuple[Provider, str]]:
        return [(Provider.parse(p), m) for p, m in self.providers.items()]

    @property
    def planned_answers(self) -> int:
        return len(self.prompts) * len(self.providers) * self.runs

    def fingerprint(self) -> str:
        """SHA-256 of the protocol, recorded in every snapshot."""
        data = self.model_dump(by_alias=True, mode="json")
        text = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_protocol(path: Path) -> IndexProtocol:
    proto = IndexProtocol.model_validate_json(path.read_text(encoding="utf-8"))
    if proto.id != path.stem:
        raise ValueError(f"{path.name}: id {proto.id!r} must match the file name")
    return proto


def load_protocols(
    directory: Path = CATEGORIES_DIR, only: list[str] | None = None
) -> list[IndexProtocol]:
    """All protocols (sorted by id), or the ones named in ``only``."""
    protocols = [load_protocol(p) for p in sorted(directory.glob("*.json"))]
    if only:
        known = {p.id for p in protocols}
        missing = [o for o in only if o not in known]
        if missing:
            raise ValueError(
                f"Unknown categories: {', '.join(missing)}. Known: {', '.join(sorted(known))}"
            )
        protocols = [p for p in protocols if p.id in only]
    return protocols
