from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


_REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
}


def _as_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return normalize_whitespace(str(value))


def _joined_value(row: pd.Series, joined_column: str, list_column: str) -> str:
    value = _as_text(row.get(joined_column))
    if value:
        return value

    raw_value = row.get(list_column)
    if isinstance(raw_value, (list, tuple)):
        return ", ".join(_as_text(item) for item in raw_value if _as_text(item))
    if isinstance(raw_value, str):
        try:
            parsed = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError):
            return _as_text(raw_value)
        if isinstance(parsed, (list, tuple)):
            return ", ".join(_as_text(item) for item in parsed if _as_text(item))
    return ""


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Build a deterministic multi-type evaluation set from cleaned papers."""
    missing_columns = sorted(_REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Cannot build test set; missing columns: {', '.join(missing_columns)}")
    if len(df) < 4:
        raise ValueError("At least 4 cleaned documents are required to build a representative test set.")

    candidates = df.copy()
    candidates["paper_id"] = candidates["paper_id"].map(_as_text)
    candidates["title"] = candidates["title"].map(_as_text)
    candidates["summary"] = candidates["summary"].map(_as_text)
    candidates = candidates[
        candidates["paper_id"].ne("")
        & candidates["title"].ne("")
        & candidates["summary"].ne("")
    ].drop_duplicates(subset=["paper_id"])
    if len(candidates) < 4:
        raise ValueError("At least 4 valid, unique cleaned documents are required to build the test set.")

    # Evenly spaced rows make the set deterministic while covering the full cleaned corpus.
    sample_size = min(6, len(candidates))
    positions = [round(index * (len(candidates) - 1) / (sample_size - 1)) for index in range(sample_size)]
    selected = candidates.iloc[positions]

    test_set: list[dict[str, Any]] = []
    for sample_index, (_, row) in enumerate(selected.iterrows(), start=1):
        paper_id = _as_text(row["paper_id"])
        title = _as_text(row["title"])
        summary = first_sentence(_as_text(row["summary"]))
        authors = _joined_value(row, "authors_joined", "authors") or "No authors listed"
        categories = _joined_value(row, "categories_joined", "categories") or "No categories listed"
        published = _as_text(row["published"])
        questions = (
            ("summary", f'What is the main point of the paper "{title}"?', summary),
            ("authors", f'Who are the authors of the paper "{title}"?', authors),
            ("date", f'When was the paper "{title}" published?', published),
            ("categories", f'What categories are associated with the paper "{title}"?', categories),
        )
        for question_type, question, ground_truth in questions:
            test_set.append(
                {
                    "id": f"eval-{sample_index:02d}-{question_type}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    write_json(Path(output_path), test_set)
    return test_set
