# Phase 1 - Baseline Report

## Source

- Source: Crossref REST API
- Query: `agentic retrieval augmented generation large language model`
- Filter: `from-pub-date:2026-02-07,has-abstract:true`
- Raw records fetched: 24
- Clean records: 24

## Evaluation Metrics

- Samples: 18
- Retrieval hit rate: 1.0000
- Mean token F1: 0.7554
- Judge accuracy: 0.6667
- Mean judge score: 3.9444

## Data Quality

- Overall: PASS (6/6 checks)
- [PASS] `row_count_min`: 24 rows
- [PASS] `paper_id_not_null`: 0 blank paper_id values
- [PASS] `paper_id_unique`: 0 duplicate paper_id values
- [PASS] `title_not_null`: 0 blank title values
- [PASS] `summary_length`: 0 rows with summary shorter than 20 chars
- [PASS] `freshness`: 0 rows older than 180 days

## Freshness

- Latest published: 2026-08-01
- Oldest published: 2026-02-12
- Stale rows: 0 / 24
- Is fresh: YES
