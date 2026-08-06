from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt_float(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, (int, float)) else "N/A"


def _format_checks(checks: list[dict[str, Any]]) -> str:
    lines = [f"- [{'PASS' if check['passed'] else 'FAIL'}] `{check['check']}`: {check['detail']}" for check in checks]
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline phase markdown report."""
    lines = [
        "# Phase 1 - Baseline Report",
        "",
        "## Source",
        "",
        f"- Source: {source_summary.get('source_api', 'N/A')}",
        f"- Query: `{source_summary.get('source_query', '')}`",
        f"- Filter: `{source_summary.get('source_filter', '')}`",
        f"- Raw records fetched: {source_summary.get('raw_record_count', 'N/A')}",
        f"- Clean records: {source_summary.get('clean_record_count', 'N/A')}",
        "",
        "## Evaluation Metrics",
        "",
        f"- Samples: {metrics.get('samples', 'N/A')}",
        f"- Retrieval hit rate: {_fmt_float(metrics.get('retrieval_hit_rate'))}",
        f"- Mean token F1: {_fmt_float(metrics.get('mean_token_f1'))}",
        f"- Judge accuracy: {_fmt_float(metrics.get('judge_accuracy'))}",
        f"- Mean judge score: {_fmt_float(metrics.get('mean_judge_score'))}",
        "",
        "## Data Quality",
        "",
        f"- Overall: {'PASS' if quality.get('passed') else 'FAIL'} "
        f"({quality.get('checks_passed', 0)}/{quality.get('checks_total', 0)} checks)",
        _format_checks(quality.get("checks", [])),
        "",
        "## Freshness",
        "",
        f"- Latest published: {freshness.get('latest_published', 'N/A')}",
        f"- Oldest published: {freshness.get('oldest_published', 'N/A')}",
        f"- Stale rows: {freshness.get('stale_rows', 'N/A')} / {freshness.get('total_rows', 'N/A')}",
        f"- Is fresh: {'YES' if freshness.get('is_fresh') else 'NO'}",
        "",
    ]
    write_text(report_path, "\n".join(lines))


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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
