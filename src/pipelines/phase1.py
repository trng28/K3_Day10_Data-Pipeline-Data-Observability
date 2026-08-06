from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

_DEMO_QUESTION_COUNT = 3


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)[: settings.max_results]

    df = build_clean_dataframe(records, run_date)
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(df, settings)

    corpus_ids = set(df["paper_id"].astype(str))
    cached_test_set = read_json(settings.paths.eval_testset) if settings.paths.eval_testset.exists() else []
    test_set_matches_corpus = bool(cached_test_set) and all(
        any(doc_id in corpus_ids for doc_id in item.get("ground_truth_doc_ids", []))
        for item in cached_test_set
    )
    if settings.refresh_test_set or not test_set_matches_corpus:
        test_set = build_test_set(df, settings.paths.eval_testset)
    else:
        test_set = cached_test_set

    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(df, settings, report_name="baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_record_count": len(records),
        "clean_record_count": len(df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )

    demo_answers = []
    try:
        agent = build_agent(settings, index)
        for item in test_set[:_DEMO_QUESTION_COUNT]:
            try:
                answer = run_agent_question(agent, item["question"])
            except Exception as exc:
                answer = f"Agent demo unavailable; baseline artifacts are still valid. {exc}"
            demo_answers.append({"question": item["question"], "answer": answer})
    except Exception as exc:
        demo_answers = [{"question": "Agent initialization", "answer": f"Skipped: {exc}"}]
    write_json(settings.paths.demo_answers, demo_answers)

    print(f"Raw records: {len(records)} | Clean records: {len(df)}")
    print(f"Metrics: {bundle.summary}")
    print(
        f"Data quality passed: {quality['success']} "
        f"({quality['passed_checks']}/{quality['total_checks']})"
    )
    print(f"Freshness is_fresh: {freshness['is_fresh']}")
    print(f"Report written to: {settings.paths.baseline_report}")
