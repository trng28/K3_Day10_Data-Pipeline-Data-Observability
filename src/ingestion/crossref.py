from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"

_TAG_RE = re.compile(r"<[^>]+>")
_RETRY_STATUS_CODES = {429, 503}


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


def _strip_abstract_markup(value: str) -> str:
    return normalize_whitespace(_TAG_RE.sub(" ", value))


def _date_from_parts(date_field: dict | None) -> str:
    if not date_field:
        return ""
    parts = (date_field.get("date-parts") or [[]])[0]
    if not parts:
        return ""
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except (TypeError, ValueError):
        return ""


def _best_published_date(item: dict) -> str:
    for key in ("published-print", "published-online", "issued", "created"):
        value = _date_from_parts(item.get(key))
        if value:
            return value
    return ""


def _updated_date(item: dict) -> str:
    indexed_at = (item.get("indexed") or {}).get("date-time")
    if indexed_at:
        return indexed_at
    return _best_published_date(item)


def _authors_from_item(item: dict) -> list[str]:
    authors: list[str] = []
    for author in item.get("author") or []:
        name = author.get("name") or f"{author.get('given', '')} {author.get('family', '')}"
        name = normalize_whitespace(name)
        if name:
            authors.append(name)
    return authors


def _categories_from_item(item: dict) -> list[str]:
    categories: list[str] = []
    for subject in item.get("subject") or []:
        subject = normalize_whitespace(str(subject))
        if subject and subject not in categories:
            categories.append(subject)
    return categories


def _pdf_url_from_item(item: dict) -> str:
    for link in item.get("link") or []:
        if link.get("content-type") == "application/pdf":
            return link.get("URL", "")
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a raw Crossref `/works` response into a list of `PaperRecord`.

    Records missing a DOI, title, or resolvable publication date are dropped
    as invalid; duplicate DOIs are collapsed to the first occurrence.
    """
    items = (payload.get("message") or {}).get("items") or []
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()

    for item in items:
        doi = item.get("DOI")
        titles = item.get("title") or []
        published = _best_published_date(item)
        if not doi or not titles or not published:
            continue

        title = normalize_whitespace(titles[0])
        if not title:
            continue

        paper_id = doi.strip().lower()
        if paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        categories = _categories_from_item(item)
        containers = item.get("container-title") or []
        abstract = item.get("abstract") or ""

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=_strip_abstract_markup(abstract),
                authors=_authors_from_item(item),
                categories=categories,
                primary_category=categories[0] if categories else "unknown",
                published=published,
                updated=_updated_date(item),
                abs_url=item.get("URL") or f"https://doi.org/{doi}",
                pdf_url=_pdf_url_from_item(item),
                comment=normalize_whitespace(containers[0]) if containers else "",
            )
        )

    return records


def _get_with_retry(params: dict, max_attempts: int = 5, timeout: int = 30) -> requests.Response:
    backoff_seconds = 1.0
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(CROSSREF_API_URL, params=params, timeout=timeout)
        except requests.RequestException as exc:
            last_error = exc
            # WinError 10013 is a local firewall/socket policy denial. Retrying
            # cannot recover it and only makes the UI appear stuck for 15s.
            if "WinError 10013" in str(exc):
                break
        else:
            if response.status_code == 200:
                return response
            if response.status_code not in _RETRY_STATUS_CODES:
                response.raise_for_status()
            last_error = RuntimeError(f"Crossref returned HTTP {response.status_code}")

        if attempt < max_attempts:
            time.sleep(backoff_seconds)
            backoff_seconds *= 2

    raise RuntimeError(f"Crossref request failed after {max_attempts} attempts") from last_error


def fetch_source_records(settings: Settings, *, allow_cached_fallback: bool = True) -> list[PaperRecord]:
    """Fetch works from the Crossref API, persist raw artifacts, and parse them.

    Saves the untouched API response to `settings.paths.raw_api_response` and
    the parsed records to `settings.paths.raw_records_json` so the crawl can
    be replayed from disk via `load_raw_records` without hitting the network.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    try:
        response = _get_with_retry(params)
    except RuntimeError as exc:
        cache_path = settings.paths.raw_records_json
        if not allow_cached_fallback or not cache_path.exists():
            raise
        records = load_raw_records(cache_path)
        if not records:
            raise RuntimeError("Crossref is unavailable and the cached snapshot is empty.") from exc
        print(
            "WARNING: Crossref is unavailable; using cached raw snapshot "
            f"({len(records)} records) from {cache_path}"
        )
        return records
    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a `raw_records_json` snapshot back into `PaperRecord` instances."""
    payload = read_json(path)
    return [PaperRecord(**item) for item in payload]
