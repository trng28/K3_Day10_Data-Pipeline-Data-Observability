from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _missing_mask(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype(str).str.strip().eq("")


def _check(name: str, success: bool, observed: Any, expectation: str) -> dict[str, Any]:
    return {
        "name": name,
        "success": bool(success),
        "observed": observed,
        "expectation": expectation,
    }


def _report_path(settings: Settings, report_name: str) -> Path:
    filename = re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(str(report_name)).name).strip(".-")
    filename = filename or "quality_report"
    if not filename.lower().endswith(".json"):
        filename += ".json"
    return settings.paths.quality_dir / filename


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run core schema, completeness, uniqueness, and freshness checks."""
    row_count = int(len(df))
    checks: list[dict[str, Any]] = [
        _check("row_count", row_count > 0, row_count, "at least 1 row"),
    ]

    if "paper_id" in df:
        missing_ids = int(_missing_mask(df["paper_id"]).sum())
        duplicate_ids = int(df.loc[~_missing_mask(df["paper_id"]), "paper_id"].duplicated().sum())
        checks.extend(
            [
                _check("paper_id_not_null", missing_ids == 0, missing_ids, "0 missing values"),
                _check("paper_id_unique", duplicate_ids == 0, duplicate_ids, "0 duplicate values"),
            ]
        )
    else:
        checks.extend(
            [
                _check("paper_id_not_null", False, "column missing", "0 missing values"),
                _check("paper_id_unique", False, "column missing", "0 duplicate values"),
            ]
        )

    if "title" in df:
        missing_titles = int(_missing_mask(df["title"]).sum())
        checks.append(_check("title_not_null", missing_titles == 0, missing_titles, "0 missing values"))
    else:
        checks.append(_check("title_not_null", False, "column missing", "0 missing values"))

    if "summary" in df:
        summary_lengths = df["summary"].fillna("").astype(str).str.strip().str.len()
        short_summaries = int(summary_lengths.lt(80).sum())
        checks.append(
            _check("summary_min_length", short_summaries == 0, short_summaries, "all summaries >= 80 characters")
        )
    else:
        checks.append(_check("summary_min_length", False, "column missing", "all summaries >= 80 characters"))

    if "age_days" in df:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        invalid_ages = int(ages.isna().sum())
        stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())
        checks.append(
            _check(
                "freshness_threshold",
                invalid_ages == 0 and stale_rows == 0,
                {"stale_rows": stale_rows, "invalid_rows": invalid_ages},
                f"all age_days <= {settings.freshness_threshold_days}",
            )
        )
    else:
        checks.append(
            _check(
                "freshness_threshold",
                False,
                "column missing",
                f"all age_days <= {settings.freshness_threshold_days}",
            )
        )

    failed_checks = [check["name"] for check in checks if not check["success"]]
    payload = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "success": not failed_checks,
        "total_rows": row_count,
        "passed_checks": len(checks) - len(failed_checks),
        "total_checks": len(checks),
        "failed_checks": failed_checks,
        "checks": checks,
    }
    write_json(_report_path(settings, report_name), payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication-date freshness and persist it as JSON."""
    if "published" in df:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    else:
        published = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")

    valid_dates = published.dropna()
    now = pd.Timestamp.now(tz="UTC")
    ages = (now - published).dt.days
    stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())
    invalid_date_rows = int(published.isna().sum())
    total_rows = int(len(df))

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "threshold_days": settings.freshness_threshold_days,
        "latest_published": valid_dates.max().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().isoformat() if not valid_dates.empty else None,
        "stale_rows": stale_rows,
        "invalid_date_rows": invalid_date_rows,
        "total_rows": total_rows,
        "is_fresh": total_rows > 0 and stale_rows == 0 and invalid_date_rows == 0,
    }
    write_json(Path(report_path), payload)
    return payload
