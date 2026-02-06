"""Industry-specific prompt templates for PromptBeacon."""

from __future__ import annotations

# Each industry maps to a list of prompt templates that use {category}
# as a placeholder.  They are designed to surface how LLMs talk about
# brands in the contexts most relevant to that industry.

INDUSTRY_TEMPLATES: dict[str, list[str]] = {
    "ecommerce": [
        "What are the best online stores for {category}?",
        "Which {category} retailer has the best customer service?",
        "Where should I buy {category} online?",
        "What are the most trusted {category} e-commerce sites?",
        "Which online {category} store offers the best deals?",
        "Can you compare {category} online retailers?",
        "What {category} website has the fastest shipping?",
        "What is the best marketplace for {category}?",
        "Which {category} store has the best return policy?",
        "What are the top-rated {category} online shops?",
    ],
    "saas": [
        "What is the best {category} software?",
        "Can you compare {category} SaaS tools?",
        "Which {category} platform is best for startups?",
        "What are the top {category} solutions for enterprises?",
        "What {category} tool has the best integrations?",
        "Which {category} software is easiest to use?",
        "What are alternatives to popular {category} tools?",
        "Which {category} platform offers the best value?",
        "What {category} software do most companies use?",
        "What is the leading {category} solution?",
    ],
    "finance": [
        "What are the best {category} financial services?",
        "Which {category} bank or institution is most trusted?",
        "Can you recommend a {category} provider?",
        "What are the top {category} fintech companies?",
        "Which {category} service has the lowest fees?",
        "What is the safest {category} platform?",
        "Which {category} provider is best for beginners?",
        "What are the most innovative {category} companies?",
        "Can you compare {category} financial products?",
        "What {category} company has the best mobile app?",
    ],
    "healthcare": [
        "What are the best {category} healthcare providers?",
        "Which {category} company is most trusted by patients?",
        "Can you recommend a {category} health solution?",
        "What are the top-rated {category} services?",
        "Which {category} provider has the best outcomes?",
        "What is the leading {category} healthcare brand?",
        "Can you compare {category} health products?",
        "Which {category} company is most innovative?",
        "What {category} brand do doctors recommend?",
        "What are the safest {category} products?",
    ],
    "travel": [
        "What are the best {category} travel companies?",
        "Which {category} booking site is most reliable?",
        "Can you recommend a {category} travel service?",
        "What are the top {category} airlines or hotels?",
        "Which {category} travel brand has the best rewards?",
        "What is the most affordable {category} option?",
        "Can you compare {category} travel providers?",
        "Which {category} company has the best reviews?",
        "What {category} brand offers the best experience?",
        "What are the most popular {category} travel apps?",
    ],
    "food": [
        "What are the best {category} food brands?",
        "Which {category} restaurant chain is most popular?",
        "Can you recommend a {category} food delivery service?",
        "What are the top {category} grocery brands?",
        "Which {category} brand is healthiest?",
        "What is the best {category} meal kit service?",
        "Can you compare {category} food brands?",
        "Which {category} company has the best quality?",
        "What {category} brand is most sustainable?",
        "What are the highest-rated {category} products?",
    ],
    "tech": [
        "What are the best {category} tech companies?",
        "Which {category} brand makes the best products?",
        "Can you recommend a {category} device or service?",
        "What are the top {category} brands for consumers?",
        "Which {category} company is most innovative?",
        "What is the best {category} for professionals?",
        "Can you compare {category} tech products?",
        "Which {category} brand offers the best value?",
        "What {category} brand has the best ecosystem?",
        "What are the most reliable {category} brands?",
    ],
}

AVAILABLE_INDUSTRIES = sorted(INDUSTRY_TEMPLATES.keys())


def get_industry_prompts(industry: str) -> list[str]:
    """Get prompt templates for a specific industry.

    Args:
        industry: Industry name (case-insensitive).

    Returns:
        List of prompt templates with ``{category}`` placeholders.

    Raises:
        ValueError: If the industry is not recognized.
    """
    key = industry.lower().strip()
    if key not in INDUSTRY_TEMPLATES:
        available = ", ".join(AVAILABLE_INDUSTRIES)
        raise ValueError(f"Unknown industry: {industry!r}. Available: {available}")
    return INDUSTRY_TEMPLATES[key]
