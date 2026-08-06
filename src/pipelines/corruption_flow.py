from __future__ import annotations


import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow.

    1. Load baseline metrics va clean dataset.
    2. Tao corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index va evaluate.
    5. Run quality checks/freshness tren corrupted data.
    6. Repair lai tu raw records.
    7. Evaluate repaired dataset.
    8. Tao comparison report.
    """
    settings = load_settings()
    run_date = now_utc()

    print("=== STARTING CORRUPTION & RECOVERY PIPELINE ===")

    # 1. Load baseline metrics va clean dataset
    if not settings.paths.clean_csv.exists() or not settings.paths.baseline_metrics.exists():
        raise RuntimeError("Missing baseline artifacts. Please run phase 1 first.")

    print("\n1. Loading baseline clean dataset and metrics...")
    df_clean = pd.read_csv(settings.paths.clean_csv)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"   Baseline rows: {len(df_clean)}")

    # 2. Tao corrupted dataframe
    print("\n2. Corrupting clean dataset...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    print(f"   Corrupted rows: {len(df_corrupted)}")

    # 3. Save corrupted artifacts
    print("\n3. Saving corrupted datasets...")
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, df_corrupted.to_dict(orient="records"))

    # 4. Rebuild index va evaluate tren corrupted data
    print("\n4. Building embeddings and collection for corrupted data...")
    index_corrupted = LocalEmbeddingIndex.build(df_corrupted, settings, settings.paths.corrupted_embeddings_json)

    print("   Evaluating agent on corrupted dataset...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=index_corrupted,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    # 5. Run quality checks/freshness tren corrupted data
    print("\n5. Running quality checks on corrupted dataset...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        df_corrupted, settings, settings.paths.quality_dir / "corrupted_freshness.json"
    )

    # 6. Repair lai tu raw records
    print("\n6. Repairing dataset from raw source...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, run_date)
    print(f"   Repaired rows: {len(df_repaired)}")

    # Save repaired artifacts
    print("   Saving repaired datasets...")
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, df_repaired.to_dict(orient="records"))

    # 7. Rebuild index va evaluate repaired dataset
    print("\n7. Building embeddings and collection for repaired data...")
    index_repaired = LocalEmbeddingIndex.build(df_repaired, settings, settings.paths.repaired_embeddings_json)

    print("   Evaluating agent on repaired dataset...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=index_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    # Run quality checks/freshness on repaired data
    print("   Running quality checks on repaired dataset...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        df_repaired, settings, settings.paths.quality_dir / "repaired_freshness.json"
    )

    # 8. Tao comparison report
    print("\n8. Generating comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("\n=== CORRUPTION & RECOVERY PIPELINE PASSED SUCCESSFULLY ===")
    print(f"Baseline F1: {baseline_metrics.get('mean_token_f1'):.4f} | "
          f"Corrupted F1: {corrupted_bundle.summary.get('mean_token_f1'):.4f} | "
          f"Repaired F1: {repaired_bundle.summary.get('mean_token_f1'):.4f}")
    print(f"Comparison report saved to: {settings.paths.comparison_report}")

