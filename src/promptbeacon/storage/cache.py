"""File-based response caching for PromptBeacon."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class ResponseCache:
    """File-based cache for LLM responses.

    Caches prompt+provider+model combinations to avoid re-querying
    for identical requests within a configurable TTL.

    Cache files are stored as JSON in ``~/.promptbeacon/cache/`` by default.
    Each entry is keyed by a SHA-256 hash of (prompt, provider, model).
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_seconds: int = 86400,
    ):
        """Initialize the cache.

        Args:
            cache_dir: Directory for cache files. Defaults to ``~/.promptbeacon/cache/``.
            ttl_seconds: Time-to-live in seconds. Defaults to 24 hours.
        """
        self._cache_dir = cache_dir or (Path.home() / ".promptbeacon" / "cache")
        self._ttl_seconds = ttl_seconds
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _make_key(prompt: str, provider: str, model: str) -> str:
        """Create a deterministic cache key."""
        raw = f"{prompt}|{provider}|{model}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _path_for_key(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def get(self, prompt: str, provider: str, model: str) -> str | None:
        """Retrieve a cached response.

        Args:
            prompt: The prompt that was sent.
            provider: Provider name.
            model: Model name.

        Returns:
            The cached response text, or ``None`` if not cached or expired.
        """
        key = self._make_key(prompt, provider, model)
        path = self._path_for_key(key)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            if time.time() - data["timestamp"] > self._ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            return data["response"]
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)
            return None

    def set(self, prompt: str, provider: str, model: str, response: str) -> None:
        """Store a response in the cache.

        Args:
            prompt: The prompt that was sent.
            provider: Provider name.
            model: Model name.
            response: The LLM response text to cache.
        """
        key = self._make_key(prompt, provider, model)
        path = self._path_for_key(key)

        data = {
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "response": response,
            "timestamp": time.time(),
        }

        try:
            path.write_text(json.dumps(data))
        except OSError:
            logger.debug("Failed to write cache entry %s", key)

    def clear(self) -> int:
        """Remove all cache entries.

        Returns:
            Number of entries removed.
        """
        count = 0
        for path in self._cache_dir.glob("*.json"):
            path.unlink(missing_ok=True)
            count += 1
        return count

    def evict_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries evicted.
        """
        count = 0
        now = time.time()
        for path in self._cache_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if now - data.get("timestamp", 0) > self._ttl_seconds:
                    path.unlink(missing_ok=True)
                    count += 1
            except (json.JSONDecodeError, OSError):
                path.unlink(missing_ok=True)
                count += 1
        return count
