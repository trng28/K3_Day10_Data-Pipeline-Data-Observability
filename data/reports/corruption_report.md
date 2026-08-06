# Corruption and Repair Report

## Evaluation Comparison

| Metric | Baseline | Corrupted | Delta vs baseline | Repaired | Delta vs baseline |
|---|---:|---:|---:|---:|---:|
| Samples | 18 | 18 | +0.0000 | 18 | +0.0000 |
| Retrieval hit rate | 1.0000 | 0.6667 | -0.3333 | 1.0000 | +0.0000 |
| Mean token F1 | 0.7554 | 0.2812 | -0.4742 | 0.7554 | +0.0000 |
| Judge accuracy | 0.6667 | 0.2222 | -0.4444 | 0.6667 | +0.0000 |
| Mean judge score | 3.6667 | 1.8889 | -1.7778 | 3.6667 | +0.0000 |

## Quality and Freshness Signals

| Signal | Corrupted | Repaired |
|---|---|---|
| Data quality | FAIL | PASS |
| Failed quality checks | ['paper_id_unique', 'summary_min_length', 'freshness_threshold'] | [] |
| Freshness | FAIL | PASS |
| Stale rows | 74 | 0 |
| Invalid date rows | 0 | 0 |
| Total rows | 130 | 100 |

## Recovery Summary

- Retrieval hit rate changed by -0.3333 after corruption and +0.0000 after repair.
- Mean token F1 changed by -0.4742 after corruption and +0.0000 after repair.
- Repaired data quality status: PASS; repaired freshness status: PASS.
