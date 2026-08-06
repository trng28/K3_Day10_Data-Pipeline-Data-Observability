from __future__ import annotations

import json
import sys

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    payload = json.loads(sys.stdin.read() or "{}")
    question = str(payload.get("question", "")).strip()
    if not question:
        raise ValueError("Question is required.")
    settings = load_settings()
    if not settings.paths.embeddings_json.exists():
        raise RuntimeError("Baseline index is missing. Run the baseline step first.")
    index = LocalEmbeddingIndex.load(settings)
    result = answer_question(question, settings, index)
    print("__CHAT_RESULT__" + json.dumps({
        "question": result.question,
        "answer": result.answer,
        "retrievedDocIds": result.retrieved_doc_ids,
        "retrievedTitles": result.retrieved_titles,
        "contexts": result.retrieved_contexts,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
