from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

_MIN_SUMMARY_CHARS = 20


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run a fixed set of data quality checks over a cleaned dataframe."""
    row_count = len(df)
    blank_paper_ids = int((df["paper_id"].astype(str).str.strip() == "").sum())
    duplicate_paper_ids = row_count - int(df["paper_id"].nunique())
    blank_titles = int((df["title"].astype(str).str.strip() == "").sum())
    short_summaries = int((df["summary"].astype(str).str.len() < _MIN_SUMMARY_CHARS).sum())
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    checks = [
        {"check": "row_count_min", "passed": row_count > 0, "detail": f"{row_count} rows"},
        {"check": "paper_id_not_null", "passed": blank_paper_ids == 0, "detail": f"{blank_paper_ids} blank paper_id values"},
        {"check": "paper_id_unique", "passed": duplicate_paper_ids == 0, "detail": f"{duplicate_paper_ids} duplicate paper_id values"},
        {"check": "title_not_null", "passed": blank_titles == 0, "detail": f"{blank_titles} blank title values"},
        {
            "check": "summary_length",
            "passed": short_summaries == 0,
            "detail": f"{short_summaries} rows with summary shorter than {_MIN_SUMMARY_CHARS} chars",
        },
        {
            "check": "freshness",
            "passed": stale_rows == 0,
            "detail": f"{stale_rows} rows older than {settings.freshness_threshold_days} days",
        },
    ]
    checks_passed = sum(1 for check in checks if check["passed"])

    report = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "row_count": row_count,
        "checks": checks,
        "checks_passed": checks_passed,
        "checks_total": len(checks),
        "passed": checks_passed == len(checks),
    }
    write_json(settings.paths.quality_dir / f"{report_name}_quality.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication freshness for a cleaned dataframe."""
    published = pd.to_datetime(df["published"])
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    report = {
        "generated_at": now_utc().isoformat(),
        "latest_published": published.max().date().isoformat(),
        "oldest_published": published.min().date().isoformat(),
        "total_rows": len(df),
        "stale_rows": stale_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0,
    }
    write_json(report_path, report)
    return report
