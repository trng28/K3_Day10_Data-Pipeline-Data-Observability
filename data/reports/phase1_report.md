# Phase 1 Baseline Report

## Source Summary

| Field | Value |
|---|---|
| source_api | Crossref REST API |
| source_query | agentic retrieval augmented generation large language model |
| source_filter | from-pub-date:2026-02-07,has-abstract:true |
| raw_record_count | 24 |
| clean_record_count | 24 |

## Evaluation Metrics

| Metric | Value |
|---|---:|
| Samples | 24 |
| Retrieval hit rate | 1.0000 |
| Mean token F1 | 0.5000 |
| Judge accuracy | 0.7083 |
| Mean judge score | 3.8333 |

## Data Quality

Overall status: **PASS**

| Check | Status | Observed | Expectation |
|---|---|---|---|
| row_count | PASS | 24 | at least 1 row |
| paper_id_not_null | PASS | 0 | 0 missing values |
| paper_id_unique | PASS | 0 | 0 duplicate values |
| title_not_null | PASS | 0 | 0 missing values |
| summary_min_length | PASS | 0 | all summaries >= 80 characters |
| freshness_threshold | PASS | {'stale_rows': 0, 'invalid_rows': 0} | all age_days <= 180 |

## Freshness

| Signal | Value |
|---|---|
| Latest published | 2026-08-01T00:00:00+00:00 |
| Oldest published | 2026-02-12T00:00:00+00:00 |
| Stale rows | 0 |
| Invalid date rows | 0 |
| Total rows | 24 |
| Freshness status | PASS |
