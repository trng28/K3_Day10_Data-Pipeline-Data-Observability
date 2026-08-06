from __future__ import annotations

from core.config import load_settings
from ingestion.crossref import fetch_source_records


def main() -> None:
    settings = load_settings()
    records = fetch_source_records(settings)

    print(f"Source: {settings.source_api}")
    print(f"Query: {settings.source_query!r} | Filter: {settings.source_filter!r} | Rows: {settings.max_results}")
    print(f"Fetched {len(records)} valid records")
    print(f"Raw API response saved to: {settings.paths.raw_api_response}")
    print(f"Raw records saved to: {settings.paths.raw_records_json}")


if __name__ == "__main__":
    main()
