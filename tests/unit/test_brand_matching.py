"""Whole-name brand matching, list-anchored ranks and appearance order."""

from __future__ import annotations

import pytest

from promptbeacon.analysis.category import parse_category
from promptbeacon.analysis.scorer import calculate_metrics
from promptbeacon.core.schemas import Citation, ProviderResult
from promptbeacon.extraction.citations import extract_citations
from promptbeacon.extraction.llm_extraction import parse_llm_extraction
from promptbeacon.extraction.matching import (
    brand_pattern,
    first_brand_offset,
    mentions_any,
    mentions_brand,
)
from promptbeacon.extraction.mentions import (
    calculate_mention_prominence,
    count_brand_mentions,
    extract_mentions,
    get_mention_positions,
    is_brand_anti_recommended,
    is_brand_recommended,
)
from promptbeacon.extraction.ranking import extract_rankings
from promptbeacon.funnel.pipeline import _text_has_any
from promptbeacon.providers.grounding import associate_brands


class TestWholeNameMatching:
    @pytest.mark.parametrize(
        ("text", "name"),
        [
            ("Use uvicorn to serve it.", "uv"),
            ("Preact is lighter.", "React"),
            ("Most array libraries copy.", "Ray"),
            ("Try httpx2 today.", "httpx"),
            ("ASP.NETwork is not a product.", ".NET"),
            ("Node.json files", "Node.js"),
            ("scikit-learnings", "scikit-learn"),
            ("Überflüssig", "Über"),
            ("pytest-asyncio is a plugin.", "pytest"),
            ("React-Native apps", "React"),
            ("", "uv"),
            ("anything", ""),
        ],
    )
    def test_does_not_match_inside_another_word(self, text, name):
        assert not mentions_brand(text, name)

    @pytest.mark.parametrize(
        ("text", "name"),
        [
            ("Install uv, then run it.", "uv"),
            ("(uv) is fast", "uv"),
            ("React's hooks", "React"),
            ("Write it in C++ or Rust.", "C++"),
            ("C++17 added it.", "C++"),
            ("Try .NET 9 for this.", ".NET"),
            ("ASP.NET is built on .NET.", ".NET"),
            ("Node.js, Deno and Bun.", "Node.js"),
            ("Use scikit-learn.", "scikit-learn"),
            ("C# and F# are both fine.", "C#"),
            ("I like Über for this.", "Über"),
            ("Ask Zürich Labs.", "Zürich Labs"),
            ("NEW BALANCE runs\nwell; New\nBalance again.", "New Balance"),
            ("httpx.", "HTTPX"),
        ],
    )
    def test_matches_the_whole_name(self, text, name):
        assert mentions_brand(text, name)

    def test_pattern_is_cached_and_case_insensitive(self):
        assert brand_pattern("uv") is brand_pattern("uv")
        assert first_brand_offset("Pick UV.", "uv") == 5
        assert first_brand_offset("uvicorn", "uv") is None

    def test_mentions_any(self):
        assert mentions_any("Pick httpx.", ["requests", "httpx"])
        assert not mentions_any("Pick httpx2.", ["requests", "httpx", ""])


class TestMentionsUseWholeNames:
    def test_reproduction_case(self):
        text = "Use uvicorn with FastAPI. Preact is lighter than most array libraries."
        result = extract_mentions(text, "uv", ["React", "Ray"])
        assert result.brands_found == []
        assert result.total_mentions == 0

    def test_counts_and_positions_skip_substrings(self):
        text = "uv is fast. uvicorn is a server. Use uv."
        assert count_brand_mentions(text, "uv") == 2
        assert get_mention_positions(text, "uv") == [0, 37]
        assert calculate_mention_prominence("uvicorn only", "uv") == 0.0

    def test_alias_with_punctuation(self):
        result = extract_mentions("Pick Node.js for this.", "Node", aliases=["Node.js"])
        assert result.brands_found == ["Node"]

    def test_recommendation_needs_the_whole_name(self):
        assert is_brand_recommended("I recommend uv for this.", "uv")
        assert not is_brand_recommended("I recommend uvicorn for this.", "uv")
        assert not is_brand_recommended("Try uvloop.", "uv")
        assert is_brand_recommended("I'd recommend\nuv here.", "uv")
        assert is_brand_anti_recommended("Avoid uv here.", "uv")
        assert not is_brand_anti_recommended("Avoid uvloop here.", "uv")
        assert is_brand_recommended("C++ is the best for this.", "C++")


class TestOtherBrandLookupsUseWholeNames:
    def test_citation_attribution(self):
        text = "Uvicorn docs are good (https://example.com/a)."
        result = extract_citations(text, ["uv"])
        assert result.citations[0].brand_associated is None

    def test_grounded_citation_attribution(self):
        cites = [Citation(source_name="x", context="uvicorn is the server")]
        assert associate_brands(cites, ["uv"])[0].brand_associated is None
        cites = [Citation(source_name="x", context="install uv first")]
        assert associate_brands(cites, ["uv"])[0].brand_associated == "uv"

    def test_funnel_source_mentions(self):
        assert not _text_has_any("Uvicorn deployment guide", ["uv"])
        assert _text_has_any("The uv guide", ["uv"])

    def test_smart_extraction_context(self):
        raw = '{"mentions": [{"brand": "uv", "sentiment": "neutral"}]}'
        text = "uvicorn runs it. " + "Filler text. " * 20 + "Then uv installs it."
        result = parse_llm_extraction(raw, text, "uv")
        assert "uv installs" in result.mentions[0].context

    def test_category_answer_containing_a_substring_of_the_brand(self):
        # "Ray" is not the brand in "array libraries"; the brand itself still is.
        assert parse_category("array libraries", "Ray") == "array libraries"
        assert parse_category("ray clusters", "Ray") is None


class TestRanksComeFromListItems:
    def test_version_numbers_are_not_ranks(self):
        text = "We recommend Python 3.12 with httpx for most teams."
        analysis = extract_rankings(text, "httpx", ["requests"])
        # A recommendation, not a numbered list item: "3.12" is a version.
        assert analysis.brand_positions == {"httpx": 1}
        assert [r.ranking_type for r in analysis.rankings] == ["recommended"]

    def test_decimals_mid_line_are_not_ranks(self):
        text = "It is 2.5 times faster than requests and 1. uv is not listed."
        analysis = extract_rankings(text, "uv", ["requests"])
        assert not analysis.has_explicit_ranking
        assert analysis.brand_positions == {}

    def test_plain_numbered_list(self):
        text = "Options:\n1. requests\n2. httpx\n3) aiohttp"
        analysis = extract_rankings(text, "httpx", ["requests", "aiohttp"])
        assert analysis.brand_positions == {"requests": 1, "httpx": 2, "aiohttp": 3}
        assert analysis.top_brand == "requests"

    def test_markdown_list_items(self):
        text = (
            "## Picks\n\n"
            "1. **requests**: the classic choice\n"
            "   2. **httpx** - async and sync\n"
            "**3. aiohttp**: async only\n"
            "### 4. urllib3\n"
        )
        analysis = extract_rankings(text, "httpx", ["requests", "aiohttp", "urllib3"])
        assert analysis.brand_positions == {
            "requests": 1,
            "httpx": 2,
            "aiohttp": 3,
            "urllib3": 4,
        }

    def test_item_title_is_matched_not_its_description(self):
        text = "1. requests: simpler than httpx\n2. httpx: async"
        analysis = extract_rankings(text, "httpx", ["requests"])
        assert analysis.brand_positions == {"requests": 1, "httpx": 2}

    def test_ranked_names_are_whole_names(self):
        text = "1. uvicorn\n2. uv"
        analysis = extract_rankings(text, "uv")
        assert analysis.brand_positions == {"uv": 2}

    def test_recommendation_sentence_keeps_dotted_names(self):
        text = "I recommend Node.js for this. Deno is fine too."
        analysis = extract_rankings(text, "Deno", ["Node.js"])
        assert analysis.brand_positions == {"Node.js": 1}

    def test_ordered_bullets_are_anchored(self):
        text = "- **Best:** httpx\n- second: requests\nthe state-of-the-art best: uv"
        analysis = extract_rankings(text, "httpx", ["requests", "uv"])
        assert analysis.brand_positions == {"httpx": 1, "requests": 2}


class TestAppearanceOrder:
    def test_position_is_order_of_first_appearance(self):
        text = "Adidas and Puma lead; Nike is third. Nike again."
        result = extract_mentions(text, "Nike", ["Adidas", "Puma"])
        by_brand = {m.brand_name: m.position for m in result.mentions}
        assert by_brand == {"Adidas": 0, "Puma": 1, "Nike": 2}
        assert result.brands_found == ["Adidas", "Puma", "Nike"]
        assert [m.brand_name for m in result.mentions] == [
            "Adidas",
            "Puma",
            "Nike",
            "Nike",
        ]

    def test_alias_counts_as_the_brand_for_order(self):
        text = "Postgres is first, then MySQL, then PostgreSQL."
        result = extract_mentions(text, "PostgreSQL", ["MySQL"], aliases=["Postgres"])
        by_brand = {m.brand_name: m.position for m in result.mentions}
        assert by_brand == {"PostgreSQL": 0, "MySQL": 1}

    def test_smart_extraction_orders_by_appearance(self):
        raw = (
            '{"mentions": [{"brand": "Nike", "sentiment": "neutral"},'
            ' {"brand": "Adidas", "sentiment": "neutral"}]}'
        )
        result = parse_llm_extraction(
            raw, "Adidas first, Nike second.", "Nike", ["Adidas"]
        )
        by_brand = {m.brand_name: m.position for m in result.mentions}
        assert by_brand == {"Adidas": 0, "Nike": 1}

    def _result(self, text: str, prompt: str = "p") -> ProviderResult:
        extraction = extract_mentions(text, "Nike", ["Adidas"])
        return ProviderResult(
            provider="openai",
            model="m",
            prompt=prompt,
            response=text,
            mentions=extraction.mentions,
            latency_ms=1.0,
        )

    def test_average_position_zero_is_reported(self):
        metrics = calculate_metrics([self._result("Nike, then Adidas.")], "Nike")
        assert metrics.average_position == 0.0

    def test_average_position_is_per_answer(self):
        results = [
            self._result("Nike, Nike, Nike, then Adidas.", "a"),
            self._result("Adidas first, Nike second.", "b"),
        ]
        metrics = calculate_metrics(results, "Nike")
        assert metrics.average_position == 0.5

    def test_average_position_none_when_never_mentioned(self):
        metrics = calculate_metrics([self._result("Adidas only.")], "Nike")
        assert metrics.average_position is None
