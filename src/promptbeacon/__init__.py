"""PromptBeacon - LLM visibility monitoring for brands.

Track how your brand appears in AI-generated responses across ChatGPT, Claude, Gemini, and more.

Example:
    >>> from promptbeacon import Beacon
    >>> beacon = Beacon("Acme Corp")
    >>> report = beacon.scan()
    >>> print(report.visibility_score)
    73.2

    >>> # Advanced usage with fluent API
    >>> from promptbeacon import Beacon, Provider
    >>> beacon = (
    ...     Beacon("Acme Corp")
    ...     .with_competitors(["Competitor A", "Competitor B"])
    ...     .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    ...     .with_categories(["product quality", "pricing"])
    ...     .with_prompt_count(50)
    ... )
    >>> report = beacon.scan()
    >>> report.to_json()
"""

from promptbeacon.beacon import Beacon
from promptbeacon.core.config import BeaconConfig, Provider
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
    VisibilityAssertionError,
)
from promptbeacon.core.schemas import (
    BrandMention,
    Citation,
    CitationSummary,
    CompetitorScore,
    Explanation,
    HistoricalDataPoint,
    HistoryReport,
    PromptStability,
    ProviderResult,
    Recommendation,
    Report,
    ScanComparison,
    ScoreBreakdown,
    SentimentBreakdown,
    ShareOfVoiceEntry,
    ShareOfVoiceReport,
    SourceAttributionEntry,
    SourceAttributionReport,
    SourceStability,
    StabilityReport,
    VisibilityMetrics,
    VolatilityMetrics,
)
from promptbeacon.funnel import FunnelReport, run_funnel
from promptbeacon.guard import BeaconGuard, GuardResult
from promptbeacon.reporting.formats import (
    to_csv,
    to_dashboard_html,
    to_dataframe,
    to_dict,
    to_html,
    to_json,
    to_markdown,
)

__version__ = "1.1.0"
__all__ = [
    # Main class
    "Beacon",
    # Guard
    "BeaconGuard",
    "GuardResult",
    # Funnel (glass-box agentic-search measurement)
    "FunnelReport",
    "run_funnel",
    # Config
    "BeaconConfig",
    "Provider",
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
    "VisibilityAssertionError",
    # Schemas
    "BrandMention",
    "Citation",
    "CitationSummary",
    "CompetitorScore",
    "Explanation",
    "HistoricalDataPoint",
    "HistoryReport",
    "PromptStability",
    "ProviderResult",
    "Recommendation",
    "Report",
    "ScanComparison",
    "ScoreBreakdown",
    "SentimentBreakdown",
    "ShareOfVoiceEntry",
    "ShareOfVoiceReport",
    "SourceAttributionEntry",
    "SourceAttributionReport",
    "SourceStability",
    "StabilityReport",
    "VisibilityMetrics",
    "VolatilityMetrics",
    # Reporting
    "to_csv",
    "to_dashboard_html",
    "to_dataframe",
    "to_dict",
    "to_html",
    "to_json",
    "to_markdown",
    # Version
    "__version__",
]
