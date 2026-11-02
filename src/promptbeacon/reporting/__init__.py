"""Reporting module for PromptBeacon."""

from promptbeacon.reporting.formats import (
    answer_rows,
    to_csv,
    to_dashboard_html,
    to_dataframe,
    to_dict,
    to_html,
    to_json,
    to_markdown,
    to_mentions_dataframe,
)
from promptbeacon.reporting.report import (
    ReportBuilder,
    create_report_builder,
    merge_reports,
)

__all__ = [
    # Formats
    "answer_rows",
    "to_csv",
    "to_dashboard_html",
    "to_dataframe",
    "to_dict",
    "to_html",
    "to_json",
    "to_markdown",
    "to_mentions_dataframe",
    # Report builder
    "ReportBuilder",
    "create_report_builder",
    "merge_reports",
]
