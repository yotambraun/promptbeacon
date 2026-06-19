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

# Buyer-intent prompt patterns — the kinds of questions real buyers ask AI when
# choosing in a category. The recommended GEO measurement protocol uses 50-200
# such prompts so visibility is characterised as a distribution, not a point.
_BUYER_INTENT_TEMPLATES: list[str] = [
    "What is the best {category}?",
    "What is the best {category} for beginners?",
    "Which {category} should I buy?",
    "Can you recommend a {category}?",
    "What are the top {category} brands?",
    "Which {category} offers the best value for money?",
    "What is the most popular {category}?",
    "Compare the leading {category} options.",
    "What {category} do experts recommend?",
    "Which {category} is best for professionals?",
    "What is the best budget {category}?",
    "What is the best premium {category}?",
    "Which {category} has the best reviews?",
    "What are good alternatives to popular {category}?",
    "Which {category} brand is most reliable?",
    "What {category} is best for small businesses?",
    "Which {category} has the best customer support?",
    "What is the best {category} for the money?",
    "Which {category} is easiest to use?",
    "What are the highest-rated {category} options?",
    "Which {category} brand is most trusted?",
    "What is the best {category} for families?",
    "Which {category} is best for enterprises?",
    "What {category} should I avoid?",
    "What is the best all-around {category}?",
]

# Appended to broaden coverage when more prompts than base templates are needed.
_BUYER_INTENT_QUALIFIERS: list[str] = [
    "",
    " in 2026",
    " right now",
    " for most people",
    " this year",
    " overall",
]


def generate_buyer_intent_prompts(category: str, n: int = 50) -> list[str]:
    """Generate ``n`` distinct buyer-intent prompts for a category.

    Buyer-intent prompts mirror how real buyers ask AI to choose within a
    category. The recommended GEO protocol uses 50-200 such prompts, re-run
    with a stable set over time, so visibility is measured as a distribution.

    Args:
        category: The product/service category (substituted into each prompt).
        n: Number of distinct prompts to return (default 50).

    Returns:
        Up to ``n`` distinct, ready-to-send prompts.

    Raises:
        ValueError: If ``n`` is less than 1.
    """
    if n < 1:
        raise ValueError("n must be >= 1")

    prompts: list[str] = []
    seen: set[str] = set()
    for qualifier in _BUYER_INTENT_QUALIFIERS:
        for template in _BUYER_INTENT_TEMPLATES:
            base = template.format(category=category)
            if qualifier and base and base[-1] in "?.":
                prompt = base[:-1] + qualifier + base[-1]
            else:
                prompt = base + qualifier
            if prompt not in seen:
                seen.add(prompt)
                prompts.append(prompt)
                if len(prompts) >= n:
                    return prompts
    return prompts


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
