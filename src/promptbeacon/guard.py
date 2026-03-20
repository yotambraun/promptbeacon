"""BeaconGuard: Real-time brand safety analysis for LLM outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from promptbeacon.core.schemas import Citation
from promptbeacon.extraction.citations import extract_citations
from promptbeacon.extraction.mentions import (
    extract_mentions,
    is_brand_recommended,
)
from promptbeacon.extraction.sentiment import (
    SentimentAnalysisResult,
    analyze_response_sentiment,
)


def is_brand_anti_recommended(context: str, brand: str) -> bool:
    """Check if a brand is being explicitly warned against in the context.

    Uses the same anti-recommendation patterns from ``is_brand_recommended``
    but returns ``True`` when a negative recommendation is detected.

    Args:
        context: The text context around the mention.
        brand: The brand name.

    Returns:
        True if the brand appears to be negatively recommended against.
    """
    context_lower = context.lower()
    brand_lower = brand.lower()

    anti_patterns = [
        f"don't recommend {brand_lower}",
        f"dont recommend {brand_lower}",
        f"do not recommend {brand_lower}",
        f"wouldn't recommend {brand_lower}",
        f"wouldnt recommend {brand_lower}",
        f"would not recommend {brand_lower}",
        f"cannot recommend {brand_lower}",
        f"can't recommend {brand_lower}",
        f"recommend against {brand_lower}",
        f"advise against {brand_lower}",
        f"avoid {brand_lower}",
        f"stay away from {brand_lower}",
        f"steer clear of {brand_lower}",
        f"not suggest {brand_lower}",
        f"never recommend {brand_lower}",
        f"stop recommending {brand_lower}",
        f"{brand_lower} is not recommended",
        f"{brand_lower} isn't recommended",
    ]

    return any(pattern in context_lower for pattern in anti_patterns)


class GuardResult(BaseModel):
    """Result of BeaconGuard analysis on a text."""

    text: str = Field(..., description="Input text that was analyzed")
    mentions_brand: bool = Field(
        default=False, description="Whether the target brand was found"
    )
    mentions_competitor: bool = Field(
        default=False, description="Whether any competitor was found"
    )
    competitor_names: list[str] = Field(
        default_factory=list, description="Which competitors were found"
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        default="neutral", description="Overall sentiment of the text"
    )
    sentiment_details: SentimentAnalysisResult = Field(
        ..., description="Full sentiment breakdown"
    )
    has_citations: bool = Field(
        default=False, description="Whether citations were found"
    )
    citations: list[Citation] = Field(
        default_factory=list, description="Citations found in the text"
    )
    is_recommendation: bool = Field(
        default=False, description="Whether the brand is explicitly recommended"
    )
    is_anti_recommendation: bool = Field(
        default=False, description="Whether the brand is explicitly warned against"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        default="low", description="Derived risk level based on flag count"
    )
    flags: list[str] = Field(
        default_factory=list, description="Human-readable triggered rules"
    )


class BeaconGuard:
    """Real-time brand safety guard for LLM outputs.

    Analyzes text for brand mentions, competitor references, sentiment,
    and recommendations. Pure local processing, no API calls.

    Example::

        guard = BeaconGuard("Nike", competitors=["Adidas", "Puma"])
        result = guard.analyze("I recommend Adidas over Nike.")
        print(result.risk_level)  # "high"
    """

    def __init__(
        self,
        brand: str,
        competitors: list[str] | None = None,
        aliases: list[str] | None = None,
        *,
        flag_competitor_mention: bool = True,
        flag_negative_sentiment: bool = True,
        flag_no_brand_mention: bool = False,
        flag_anti_recommendation: bool = True,
    ) -> None:
        self.brand = brand
        self.competitors = competitors or []
        self.aliases = aliases or []
        self.flag_competitor_mention = flag_competitor_mention
        self.flag_negative_sentiment = flag_negative_sentiment
        self.flag_no_brand_mention = flag_no_brand_mention
        self.flag_anti_recommendation = flag_anti_recommendation

    def analyze(self, text: str) -> GuardResult:
        """Analyze text for brand safety concerns.

        Synchronous, no API calls, pure local processing.

        Args:
            text: The LLM output text to analyze.

        Returns:
            GuardResult with analysis details and risk level.
        """
        if not text or not text.strip():
            sentiment_result = analyze_response_sentiment("")
            return GuardResult(
                text=text,
                sentiment_details=sentiment_result,
            )

        # 1. Extract mentions
        mention_result = extract_mentions(
            text, self.brand, self.competitors, self.aliases
        )

        # Determine brand/competitor presence
        mentions_brand = self.brand in mention_result.brands_found
        competitor_names = [
            b for b in mention_result.brands_found if b in self.competitors
        ]
        mentions_competitor = len(competitor_names) > 0

        # 2. Sentiment analysis
        sentiment_result = analyze_response_sentiment(text)
        sentiment = sentiment_result.overall_sentiment

        # 3. Citations
        all_brands = [self.brand] + self.competitors
        citation_result = extract_citations(text, all_brands)
        citations = [
            Citation(
                url=c.url,
                source_name=c.source_name,
                context=c.context,
                brand_associated=c.brand_associated,
            )
            for c in citation_result.citations
        ]

        # 4. Recommendation detection
        is_rec = is_brand_recommended(text, self.brand)
        is_anti_rec = is_brand_anti_recommended(text, self.brand)

        # 5. Build flags
        flags: list[str] = []

        if self.flag_competitor_mention and mentions_competitor:
            flags.append(f"Competitor mentioned: {', '.join(competitor_names)}")

        if self.flag_negative_sentiment and sentiment == "negative":
            flags.append("Negative sentiment detected")

        if self.flag_no_brand_mention and not mentions_brand:
            flags.append("Brand not mentioned in response")

        if self.flag_anti_recommendation and is_anti_rec:
            flags.append("Brand anti-recommendation detected")

        # 6. Compute risk level
        flag_count = len(flags)
        if flag_count == 0:
            risk_level: Literal["low", "medium", "high"] = "low"
        elif flag_count == 1:
            risk_level = "medium"
        else:
            risk_level = "high"

        return GuardResult(
            text=text,
            mentions_brand=mentions_brand,
            mentions_competitor=mentions_competitor,
            competitor_names=competitor_names,
            sentiment=sentiment,
            sentiment_details=sentiment_result,
            has_citations=len(citations) > 0,
            citations=citations,
            is_recommendation=is_rec,
            is_anti_recommendation=is_anti_rec,
            risk_level=risk_level,
            flags=flags,
        )
