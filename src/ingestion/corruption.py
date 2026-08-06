from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from core.utils import normalize_whitespace, write_json



def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhieu dang data corruption.

    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    df = df.copy()

    # Sắp xếp theo published date giảm dần
    if "published" in df.columns:
        df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    n = len(df)
    log = {
        "original_rows": n,
        "dropped_latest_count": 0,
        "blank_summary_count": 0,
        "noise_injected_count": 0,
        "blank_title_count": 0,
        "stale_published_count": 0,
        "duplicated_rows_count": 0,
    }

    # 1. Drop latest records (loại bỏ 3 dòng đầu tiên)
    num_drop = min(3, n - 1) if n > 1 else 0
    if num_drop > 0:
        df = df.iloc[num_drop:].reset_index(drop=True)
        log["dropped_latest_count"] = num_drop

    n = len(df)

    # 2. Blank summary ở một số dòng (dòng 0 và 1)
    blank_indices = [i for i in [0, 1] if i < n]
    if blank_indices:
        df.loc[blank_indices, "summary"] = ""
        log["blank_summary_count"] = len(blank_indices)

    # 3. Inject noise vào summary (dòng 2 và 3)
    noise_indices = [i for i in [2, 3] if i < n]
    if noise_indices:
        noise = " xyz GIBBERISH_NOISE_123 text error "
        df.loc[noise_indices, "summary"] = df.loc[noise_indices, "summary"] + noise
        log["noise_injected_count"] = len(noise_indices)

    # 4. Truncate title (làm trống title dòng 4 và 5 để kích hoạt blank title check)
    title_indices = [i for i in [4, 5] if i < n]
    if title_indices:
        df.loc[title_indices, "title"] = ""
        log["blank_title_count"] = len(title_indices)

    # 5. Làm published date cũ đi (dòng 6 và 7 đặt thành năm 2000 để kích hoạt stale check)
    stale_indices = [i for i in [6, 7] if i < n]
    if stale_indices:
        df.loc[stale_indices, "published"] = "2000-01-01"
        df.loc[stale_indices, "age_days"] = 9999
        log["stale_published_count"] = len(stale_indices)

    # 6. Add duplicate rows (nhân bản 2 dòng đầu tiên và nối vào cuối)
    if n >= 2:
        df_dup = df.iloc[:2]
        df = pd.concat([df, df_dup], ignore_index=True)
        log["duplicated_rows_count"] = len(df_dup)

    # 7. Rebuild summary_chars và text_for_embedding
    df["summary_chars"] = df["summary"].astype(str).str.len()

    for col in ["title", "summary", "authors_joined", "categories_joined"]:
        if col not in df.columns:
            df[col] = ""

    df["text_for_embedding"] = df.apply(
        lambda r: f"{r['title']}. {r['summary']} Authors: {r['authors_joined']}. Categories: {r['categories_joined']}.",
        axis=1
    ).apply(normalize_whitespace)

    # 8. Ghi corruption log vào output_log_path
    write_json(Path(output_log_path), log)

    return df

