"""Tests for the HTML dashboard export."""

from __future__ import annotations

from promptbeacon import Beacon, Provider, to_dashboard_html


def _demo_report():
    return (
        Beacon("Nike")
        .with_competitors("Adidas")
        .with_categories("running shoes")
        .with_prompt_count(6)
        .with_providers(Provider.OPENAI)
        .demo()
        .scan()
    )


def test_dashboard_is_self_contained_html():
    html = to_dashboard_html(_demo_report())
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    # Single-file: no external scripts/stylesheets.
    assert "<script" not in html
    assert "stylesheet" not in html


def test_dashboard_includes_key_sections():
    html = to_dashboard_html(_demo_report())
    assert "Nike" in html
    assert "Share of Voice" in html
    assert "Score Breakdown" in html
    assert "Sentiment" in html


def test_dashboard_escapes_brand_names():
    report = (
        Beacon("Tom & Jerry <Co>")
        .with_categories("widgets")
        .with_prompt_count(3)
        .demo()
        .scan()
    )
    html = to_dashboard_html(report)
    assert "Tom &amp; Jerry &lt;Co&gt;" in html


def test_dashboard_renders_stability_when_present():
    report = (
        Beacon("Nike")
        .with_categories("running shoes")
        .with_prompt_count(4)
        .with_stability(3)
        .demo()
        .scan_stability()
    )
    html = to_dashboard_html(report)
    assert "Stability" in html
