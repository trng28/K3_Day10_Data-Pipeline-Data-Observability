from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import pandas as pd

from ingestion.crossref import PaperRecord



def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    if not records:
        cols = [
            "paper_id", "title", "summary", "authors", "categories", "primary_category",
            "published", "updated", "abs_url", "pdf_url", "comment",
            "authors_joined", "categories_joined", "summary_chars", "age_days", "text_for_embedding"
        ]
        return pd.DataFrame(columns=cols)

    # 1. Chuyen doi sang list dicts va DataFrame
    dicts = [asdict(r) for r in records]
    df = pd.DataFrame(dicts)

    # 2. Normalize các trường thông tin cơ bản
    df["title"] = df["title"].fillna("").astype(str).str.strip()
    df["summary"] = df["summary"].fillna("").astype(str).str.strip()
    df["primary_category"] = df["primary_category"].fillna("N/A").astype(str).str.strip()
    df["abs_url"] = df["abs_url"].fillna("").astype(str).str.strip()
    df["pdf_url"] = df["pdf_url"].fillna("").astype(str).str.strip()
    df["comment"] = df["comment"].fillna("N/A").astype(str).str.strip()

    # 3. Tạo các cột helper joined
    df["authors_joined"] = df["authors"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
    df["categories_joined"] = df["categories"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
    df["summary_chars"] = df["summary"].str.len()

    # 4. Parse ngày và tính age_days
    # Sử dụng tz-naive datetime để so sánh
    run_date_naive = run_date.replace(tzinfo=None)
    published_dt = pd.to_datetime(df["published"], errors="coerce").dt.tz_localize(None)
    df["age_days"] = (run_date_naive - published_dt).dt.days.fillna(0).astype(int)

    # 5. Tạo text_for_embedding
    df["text_for_embedding"] = (
        "Title: " + df["title"] + "\n" +
        "Authors: " + df["authors_joined"] + "\n" +
        "Categories: " + df["categories_joined"] + "\n" +
        "Summary: " + df["summary"]
    )

    # 6. Loại trùng lặp và bản ghi xấu
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["paper_id"].notna() & (df["paper_id"].str.strip() != "")]
    df = df[df["title"].notna() & (df["title"].str.strip() != "")]
    df = df[df["summary"].notna() & (df["summary"].str.strip() != "")]
    df = df[df["summary_chars"] >= 50]  # Abstract/Summary tối thiểu 50 ký tự

    # 7. Sắp xếp theo ngày published mới nhất đến cũ nhất
    df = df.sort_values(by="published", ascending=False)

    return df

