from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import re
import time
import requests

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str




def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    message = payload.get("message", {})
    items = message.get("items", [])
    records = []

    for item in items:
        # 1. DOI lam paper_id (bat buoc)
        paper_id = item.get("DOI", "").strip()
        if not paper_id:
            continue

        # 2. Title (bat buoc)
        title_list = item.get("title", [])
        title = title_list[0].strip() if title_list else ""
        if not title:
            continue

        # 3. Abstract/Summary (bat buoc)
        raw_abstract = item.get("abstract", "").strip()
        if not raw_abstract:
            continue
        # Strip HTML/XML tags
        abstract = re.sub(r"<[^>]+>", " ", raw_abstract)
        abstract = " ".join(abstract.split()).strip()
        if not abstract:
            continue

        # 4. Authors
        authors = []
        for auth in item.get("author", []):
            given = auth.get("given", "").strip()
            family = auth.get("family", "").strip()
            name = auth.get("name", "").strip()
            if given or family:
                full_name = f"{given} {family}".strip()
                authors.append(full_name)
            elif name:
                authors.append(name)

        # 5. Categories/Subject
        categories = item.get("subject", [])
        # Ensure list of strings
        categories = [str(c).strip() for c in categories if c]
        primary_category = categories[0] if categories else "N/A"

        # 6. Dates
        published = "1970-01-01"
        for date_key in ["published-print", "published-online", "issued", "created"]:
            date_parts = item.get(date_key, {}).get("date-parts", [])
            if date_parts and date_parts[0]:
                parts = date_parts[0]
                year = parts[0]
                month = parts[1] if len(parts) > 1 else 1
                day = parts[2] if len(parts) > 2 else 1
                published = f"{year:04d}-{month:02d}-{day:02d}"
                break

        updated = "1970-01-01"
        for date_key in ["updated", "created", "indexed"]:
            date_parts = item.get(date_key, {}).get("date-parts", [])
            if date_parts and date_parts[0]:
                parts = date_parts[0]
                year = parts[0]
                month = parts[1] if len(parts) > 1 else 1
                day = parts[2] if len(parts) > 2 else 1
                updated = f"{year:04d}-{month:02d}-{day:02d}"
                break
        if updated == "1970-01-01":
            updated = published

        # 7. URLs
        abs_url = item.get("URL", "").strip()
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf" or "pdf" in link.get("URL", "").lower():
                pdf_url = link.get("URL", "").strip()
                break
        if not pdf_url:
            pdf_url = abs_url

        comment = "N/A"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=abstract,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref works API, luu raw response, parse thanh records.

    1. Tao params tu settings.
    2. Goi API voi retry cho status code 429/503.
    3. Luu raw response vao raw_api_response.
    4. Parse payload bang parse_crossref_payload.
    5. Luu records vao raw_records_json.
    """
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "Day10DataPipelineLab/1.0 (mailto:student@example.com)"
    }

    max_retries = 3
    backoff_factor = 2.0
    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=20)
            if response.status_code == 200:
                break
            elif response.status_code in [429, 503, 504]:
                time.sleep(backoff_factor ** attempt)
            else:
                response.raise_for_status()
        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff_factor ** attempt)

    if response is None or response.status_code != 200:
        raise RuntimeError(f"Failed to fetch from Crossref after {max_retries} attempts.")

    payload = response.json()

    # Luu raw api response
    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Parse
    records = parse_crossref_payload(payload)

    # Luu raw records json
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    records_dict = [asdict(r) for r in records]
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump(records_dict, f, ensure_ascii=False, indent=2)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [PaperRecord(**d) for d in data]

