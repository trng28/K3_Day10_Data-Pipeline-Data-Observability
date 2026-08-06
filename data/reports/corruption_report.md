# Corruption and Repair Report

## Evaluation Comparison

| Metric | Baseline | Corrupted | Delta vs baseline | Repaired | Delta vs baseline |
|---|---:|---:|---:|---:|---:|
| Samples | 24 | 24 | +0.0000 | 24 | +0.0000 |
| Retrieval hit rate | 1.0000 | 0.8333 | -0.1667 | 1.0000 | +0.0000 |
| Mean token F1 | 0.5000 | 0.3414 | -0.1586 | 0.5000 | +0.0000 |
| Judge accuracy | 0.7083 | 0.5417 | -0.1667 | 0.7083 | +0.0000 |
| Mean judge score | 3.8333 | 3.2083 | -0.6250 | 3.8333 | +0.0000 |

## Quality and Freshness Signals

| Signal | Corrupted | Repaired |
|---|---|---|
| Data quality | FAIL | PASS |
| Failed quality checks | ['paper_id_unique', 'summary_min_length', 'freshness_threshold'] | [] |
| Freshness | FAIL | PASS |
| Stale rows | 18 | 0 |
| Invalid date rows | 0 | 0 |
| Total rows | 32 | 24 |

## Recovery Summary

- Retrieval hit rate changed by -0.1667 after corruption and +0.0000 after repair.
- Mean token F1 changed by -0.1586 after corruption and +0.0000 after repair.
- Repaired data quality status: PASS; repaired freshness status: PASS.
