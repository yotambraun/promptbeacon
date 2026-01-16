"""Core module for PromptBeacon."""

from promptbeacon.core.config import (
    BeaconConfig,
    Provider,
    get_api_key,
    get_default_storage_path,
    has_api_key,
)
from promptbeacon.core.exceptions import (
    ConfigurationError,
    ExtractionError,
    PromptBeaconError,
    ProviderAPIError,
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ScanError,
    StorageError,
    ValidationError,
)
from promptbeacon.core.schemas import (
    BrandMention,
    CompetitorScore,
    Explanation,
    HistoricalDataPoint,
    HistoryReport,
    ProviderResult,
    Recommendation,
    Report,
    ScanComparison,
    SentimentBreakdown,
    VisibilityMetrics,
)

__all__ = [
    # Config
    "BeaconConfig",
    "Provider",
    "get_api_key",
    "get_default_storage_path",
    "has_api_key",
    # Exceptions
    "ConfigurationError",
    "ExtractionError",
    "PromptBeaconError",
    "ProviderAPIError",
    "ProviderAuthenticationError",
    "ProviderError",
    "ProviderRateLimitError",
    "ScanError",
    "StorageError",
    "ValidationError",
    # Schemas
    "BrandMention",
    "CompetitorScore",
    "Explanation",
    "HistoricalDataPoint",
    "HistoryReport",
    "ProviderResult",
    "Recommendation",
    "Report",
    "ScanComparison",
    "SentimentBreakdown",
    "VisibilityMetrics",
]
