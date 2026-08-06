from __future__ import annotations

import pandas as pd

from core.utils import normalize_whitespace, write_json


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path,
    *,
    drop_rate: float = 0.10,
    blank_rate: float = 0.12,
    noise_rate: float = 0.12,
    stale_rate: float = 0.10,
    duplicate_rate: float = 0.08,
) -> pd.DataFrame:
    """TODO(student): simulate nhieu dang data corruption.

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    original_rows = len(df)
    corrupted = df.copy(deep=True).reset_index(drop=True)

    def count(rate: float, minimum: int = 1) -> int:
        if rate <= 0:
            return 0
        return min(len(corrupted), max(minimum, round(original_rows * min(rate, 1.0))))

    dropped = count(drop_rate)
    dropped_ids = corrupted.head(dropped)["paper_id"].astype(str).tolist() if dropped else []
    if dropped:
        corrupted = corrupted.iloc[dropped:].reset_index(drop=True)

    blanked = min(count(blank_rate), len(corrupted))
    blank_indices = list(corrupted.index[:blanked])
    if blanked:
        corrupted.loc[blank_indices, "summary"] = ""
        corrupted.loc[blank_indices, "summary_chars"] = 0

    noised = min(count(noise_rate), len(corrupted))
    noise_indices = list(corrupted.index[blanked : blanked + noised])
    if noised:
        corrupted.loc[noise_indices, "summary"] = (
            corrupted.loc[noise_indices, "summary"].astype(str) + " ### CORRUPTED_TOKEN noise noise [invalid]"
        )
        corrupted.loc[noise_indices, "title"] = corrupted.loc[noise_indices, "title"].astype(str).str.slice(0, 28)

    stale = min(count(stale_rate), len(corrupted))
    stale_indices = list(corrupted.index[-stale:]) if stale else []
    if stale:
        corrupted.loc[stale_indices, "age_days"] = 3650
        corrupted.loc[stale_indices, "published"] = "2016-01-01"

    corrupted["summary_chars"] = corrupted["summary"].fillna("").astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(
        lambda row: normalize_whitespace(
            f"{row['title']}. {row['summary']} Authors: {row['authors_joined']}. "
            f"Categories: {row['categories_joined']}."
        ),
        axis=1,
    )

    duplicated = min(count(duplicate_rate), len(corrupted))
    duplicate_ids: list[str] = []
    if duplicated:
        duplicate_rows = corrupted.tail(duplicated).copy()
        duplicate_ids = duplicate_rows["paper_id"].astype(str).tolist()
        corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)

    write_json(
        output_log_path,
        {
            "seed": "deterministic-row-order",
            "original_rows": original_rows,
            "corrupted_rows": len(corrupted),
            "operations": {
                "dropped_latest": {"count": dropped, "paper_ids": dropped_ids},
                "blank_summaries": {"count": blanked},
                "noisy_truncated_records": {"count": noised},
                "stale_records": {"count": stale},
                "duplicate_records": {"count": duplicated, "paper_ids": duplicate_ids},
            },
        },
    )
    return corrupted
