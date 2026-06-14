"""Exception hierarchy for PromptBeacon."""

from __future__ import annotations


class PromptBeaconError(Exception):
    """Base exception for all PromptBeacon errors."""

    pass


class ConfigurationError(PromptBeaconError):
    """Raised when there's a configuration problem."""

    pass


class ProviderError(PromptBeaconError):
    """Base exception for provider-related errors."""

    pass


class ProviderAuthenticationError(ProviderError):
    """Raised when provider authentication fails."""

    pass


class ProviderRateLimitError(ProviderError):
    """Raised when provider rate limit is exceeded."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ProviderAPIError(ProviderError):
    """Raised when provider API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ExtractionError(PromptBeaconError):
    """Raised when brand extraction fails."""

    pass


class StorageError(PromptBeaconError):
    """Raised when storage operations fail."""

    pass


class ValidationError(PromptBeaconError):
    """Raised when data validation fails."""

    pass


class ScanError(PromptBeaconError):
    """Raised when a scan operation fails."""

    pass


class VisibilityAssertionError(AssertionError, PromptBeaconError):
    """Raised when a visibility threshold assertion fails.

    Subclasses :class:`AssertionError` so that pytest renders it as a normal
    assertion failure (and CI exits non-zero), while also being a
    :class:`PromptBeaconError` for callers that catch the package's base
    exception.

    The ``failures`` attribute holds the individual unmet thresholds.
    """

    def __init__(self, message: str, failures: list[str] | None = None):
        super().__init__(message)
        self.failures = failures or []
