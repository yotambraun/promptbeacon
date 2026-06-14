"""Tests for the CI assertion API (Report.assert_visibility)."""

from __future__ import annotations

import pytest

from promptbeacon import Beacon, Provider, VisibilityAssertionError


@pytest.fixture(scope="module")
def demo_report():
    return (
        Beacon("Nike")
        .with_competitors("Adidas")
        .with_categories("running shoes")
        .with_prompt_count(8)
        .with_providers(Provider.OPENAI)
        .demo()
        .scan()
    )


def test_assert_passes_and_returns_self(demo_report):
    assert demo_report.assert_visibility(min_score=0) is demo_report


def test_assert_score_failure(demo_report):
    with pytest.raises(VisibilityAssertionError) as exc:
        demo_report.assert_visibility(min_score=999)
    assert "visibility_score" in str(exc.value)
    assert exc.value.failures


def test_assert_share_of_voice_failure(demo_report):
    with pytest.raises(VisibilityAssertionError):
        demo_report.assert_visibility(min_share_of_voice=1.1)


def test_assert_accumulates_multiple_failures(demo_report):
    with pytest.raises(VisibilityAssertionError) as exc:
        demo_report.assert_visibility(min_score=999, min_share_of_voice=1.1)
    assert len(exc.value.failures) == 2


def test_assertion_error_is_assertionerror(demo_report):
    # So pytest renders it as a normal assertion failure / CI exits non-zero.
    with pytest.raises(AssertionError):
        demo_report.assert_visibility(min_score=999)


def test_assert_max_rank(demo_report):
    # Rank is 1 or 2 in a two-brand demo; max_rank=0 is impossible -> fails.
    with pytest.raises(VisibilityAssertionError):
        demo_report.assert_visibility(max_rank=0)
