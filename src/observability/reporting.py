from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


_METRIC_LABELS = {
    "samples": "Samples",
    "retrieval_hit_rate": "Retrieval hit rate",
    "mean_token_f1": "Mean token F1",
    "judge_accuracy": "Judge accuracy",
    "mean_judge_score": "Mean judge score",
}


def _display(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (dict, list, tuple)):
        return str(value).replace("|", "\\|")
    return str(value).replace("|", "\\|").replace("\n", " ")


def _delta(current: Any, baseline: Any) -> str:
    if not isinstance(current, (int, float)) or isinstance(current, bool):
        return "N/A"
    if not isinstance(baseline, (int, float)) or isinstance(baseline, bool):
        return "N/A"
    return f"{current - baseline:+.4f}"


def _quality_status(quality: dict[str, Any]) -> bool | None:
    value = quality.get("success", quality.get("overall_success"))
    if not isinstance(value, bool):
        value = quality.get("passed")
    return value if isinstance(value, bool) else None


def _metric_rows(metrics: dict[str, Any]) -> list[str]:
    return [
        f"| {_METRIC_LABELS[key]} | {_display(metrics.get(key))} |"
        for key in _METRIC_LABELS
    ]


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline source, evaluation, quality, and freshness report."""
    source_rows = [f"| {_display(key)} | {_display(value)} |" for key, value in source_summary.items()]
    check_rows = [
        f"| {_display(check.get('name', check.get('check')))} | "
        f"{_display(check.get('success', check.get('passed')))} | "
        f"{_display(check.get('observed', check.get('detail')))} | "
        f"{_display(check.get('expectation'))} |"
        for check in quality.get("checks", [])
    ]
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        *(source_rows or ["| Status | No source summary supplied |"]),
        "",
        "## Evaluation Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        *_metric_rows(metrics),
        "",
        "## Data Quality",
        "",
        f"Overall status: **{_display(_quality_status(quality))}**",
        "",
        "| Check | Status | Observed | Expectation |",
        "|---|---|---|---|",
        *(check_rows or ["| N/A | N/A | No checks supplied | N/A |"]),
        "",
        "## Freshness",
        "",
        "| Signal | Value |",
        "|---|---|",
        f"| Latest published | {_display(freshness.get('latest_published'))} |",
        f"| Oldest published | {_display(freshness.get('oldest_published'))} |",
        f"| Stale rows | {_display(freshness.get('stale_rows'))} |",
        f"| Invalid date rows | {_display(freshness.get('invalid_date_rows'))} |",
        f"| Total rows | {_display(freshness.get('total_rows'))} |",
        f"| Freshness status | {_display(freshness.get('is_fresh'))} |",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a baseline/corrupted/repaired comparison report with deltas."""
    metric_rows = []
    for key, label in _METRIC_LABELS.items():
        baseline = baseline_metrics.get(key)
        corrupted = corrupted_metrics.get(key)
        repaired = repaired_metrics.get(key)
        metric_rows.append(
            f"| {label} | {_display(baseline)} | {_display(corrupted)} | {_delta(corrupted, baseline)} | "
            f"{_display(repaired)} | {_delta(repaired, baseline)} |"
        )

    lines = [
        "# Corruption and Repair Report",
        "",
        "## Evaluation Comparison",
        "",
        "| Metric | Baseline | Corrupted | Delta vs baseline | Repaired | Delta vs baseline |",
        "|---|---:|---:|---:|---:|---:|",
        *metric_rows,
        "",
        "## Quality and Freshness Signals",
        "",
        "| Signal | Corrupted | Repaired |",
        "|---|---|---|",
        f"| Data quality | {_display(_quality_status(corrupted_quality))} | {_display(_quality_status(repaired_quality))} |",
        f"| Failed quality checks | {_display(corrupted_quality.get('failed_checks'))} | {_display(repaired_quality.get('failed_checks'))} |",
        f"| Freshness | {_display(corrupted_freshness.get('is_fresh'))} | {_display(repaired_freshness.get('is_fresh'))} |",
        f"| Stale rows | {_display(corrupted_freshness.get('stale_rows'))} | {_display(repaired_freshness.get('stale_rows'))} |",
        f"| Invalid date rows | {_display(corrupted_freshness.get('invalid_date_rows'))} | {_display(repaired_freshness.get('invalid_date_rows'))} |",
        f"| Total rows | {_display(corrupted_freshness.get('total_rows'))} | {_display(repaired_freshness.get('total_rows'))} |",
        "",
        "## Recovery Summary",
        "",
        f"- Retrieval hit rate changed by {_delta(corrupted_metrics.get('retrieval_hit_rate'), baseline_metrics.get('retrieval_hit_rate'))} after corruption and {_delta(repaired_metrics.get('retrieval_hit_rate'), baseline_metrics.get('retrieval_hit_rate'))} after repair.",
        f"- Mean token F1 changed by {_delta(corrupted_metrics.get('mean_token_f1'), baseline_metrics.get('mean_token_f1'))} after corruption and {_delta(repaired_metrics.get('mean_token_f1'), baseline_metrics.get('mean_token_f1'))} after repair.",
        f"- Repaired data quality status: {_display(_quality_status(repaired_quality))}; repaired freshness status: {_display(repaired_freshness.get('is_fresh'))}.",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))
