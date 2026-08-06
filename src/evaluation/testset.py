from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import write_json

_MIN_DOCUMENTS = 3
_MAX_SAMPLE_PAPERS = 6


def _select_sample(df: pd.DataFrame) -> pd.DataFrame:
    sample_size = min(_MAX_SAMPLE_PAPERS, len(df))
    step = max(1, len(df) // sample_size)
    indices = list(range(0, len(df), step))[:sample_size]
    return df.iloc[indices]


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a question/ground-truth evaluation set from the cleaned dataframe."""
    if len(df) < _MIN_DOCUMENTS:
        raise ValueError(f"Need at least {_MIN_DOCUMENTS} cleaned documents to build a test set, got {len(df)}.")

    sample = _select_sample(df)
    test_set: list[dict[str, Any]] = []
    next_id = 1

    def _add(question_type: str, question: str, ground_truth: str, doc_ids: list[str]) -> None:
        nonlocal next_id
        test_set.append(
            {
                "id": f"q{next_id}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": doc_ids,
            }
        )
        next_id += 1

    for _, row in sample.iterrows():
        doc_ids = [row["paper_id"]]
        title = row["title"]

        _add("summary", f"What is the paper '{title}' about?", row["summary"], doc_ids)
        _add("date", f"When was the paper '{title}' published?", row["published"], doc_ids)

        if row["authors_joined"]:
            _add("authors", f"Who authored the paper '{title}'?", row["authors_joined"], doc_ids)

        if row["categories_joined"]:
            _add("categories", f"What categories does the paper '{title}' belong to?", row["categories_joined"], doc_ids)

    write_json(output_path, test_set)
    return test_set
