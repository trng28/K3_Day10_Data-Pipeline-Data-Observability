from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _to_naive_timestamp(value) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return pd.NaT
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw `PaperRecord`s into a dataframe ready for embedding."""
    run_ts = _to_naive_timestamp(run_date)

    rows: list[dict] = []
    seen_ids: set[str] = set()

    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        published_ts = _to_naive_timestamp(record.published)

        if not paper_id or not title or not summary or pd.isna(published_ts):
            continue
        if paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        authors_joined = compact_join(normalize_whitespace(a) for a in record.authors)
        categories_joined = compact_join(normalize_whitespace(c) for c in record.categories)
        text_for_embedding = normalize_whitespace(
            f"{title}. {summary} Authors: {authors_joined}. Categories: {categories_joined}."
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": normalize_whitespace(record.primary_category) or "unknown",
                "published": published_ts.date().isoformat(),
                "updated": normalize_whitespace(record.updated),
                "age_days": (run_ts - published_ts).days,
                "summary_chars": len(summary),
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        raise ValueError("No valid records survived cleaning; check the raw source data.")

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
