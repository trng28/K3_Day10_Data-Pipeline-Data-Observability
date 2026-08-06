# `retrieval/`

Reference implementation (not a student stub) for the RAG retrieval stack used by the pipelines:
turns a cleaned papers dataframe into a searchable ChromaDB index, and answers questions over that
index either with a rule-based extractor (`qa.py`) or a tool-using LLM agent (`agent.py`).

## Files

| File             | Responsibility                                                                                     |
| ---------------- | --------------------------------------------------------------------------------------------------- |
| `embeddings.py`  | `MiniLMEmbeddings` — langchain `Embeddings` wrapper around `sentence-transformers/all-MiniLM-L6-v2`. |
| `index.py`       | `LocalEmbeddingIndex` — builds/loads a ChromaDB collection + JSON manifest; `search()` (top-k similarity) and `lookup()` (exact `paper_id`/title match). |
| `llm.py`         | `build_llm()` — provider-agnostic chat model factory (Gemini, OpenAI, Anthropic, OpenRouter, Ollama, custom OpenAI-compatible). |
| `qa.py`          | `answer_question()` — deterministic answer extraction from the top retrieved result, no LLM call required. |
| `agent.py`       | `build_agent()` — a langchain `create_agent` with `semantic_search_papers`/`lookup_paper` tools, backed by `build_llm()`. |

## How the pieces connect

```
cleaned dataframe (from ingestion/cleaning.py)
        │
        ▼
LocalEmbeddingIndex.build(df, settings)   ──▶  data/chroma/ (Chroma collection)
        │                                       + *_embeddings.json (manifest)
        ▼
index.search(query) / index.lookup(id_or_title)
        │                              │
        ▼                              ▼
qa.answer_question(...)          agent.build_agent(...) → run_agent_question(...)
  (no LLM call, extractive)         (LLM call via build_llm(), tool-using)
```

`evaluation/metrics.py` uses `qa.answer_question()` for scoring; the pipelines can additionally
demo `agent.py` on a few sample questions.

## Configuration

All settings come from `core.config.load_settings()` (reads `.env`, see `.env.example`). Relevant
fields for this module:

- `LLM_PROVIDER` / `LLM_MODEL` — selects the provider/model `build_llm()` constructs.
- One of `GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY`, or
  `CUSTOM_LLM_BASE_URL` (+ optional `CUSTOM_LLM_API_KEY`) for a custom OpenAI-compatible endpoint,
  or nothing for `ollama` (local). `require_llm_credentials()` raises a clear error if the
  selected provider's credential is missing.
- `embedding_model`, `top_k`, and the three Chroma collection names
  (`baseline_collection_name` / `corrupted_collection_name` / `repaired_collection_name`) are fixed
  in `core/config.py`, not env-configurable.

`embeddings.py` and `index.py` need no API key — only a one-time download of the MiniLM model on
first use. `llm.py`, `qa.py` (LLM judge is elsewhere, not in `qa.py`), and `agent.py` need a valid
LLM credential for the configured provider.

## How to run / try it standalone

The full pipelines (`pipelines/phase1.py` etc.) are still student stubs, so the easiest way to
exercise this module on its own is a short script or REPL session. From the project root, with the
project installed (`uv sync` or `pip install -e .`):

```bash
uv run python
```

```python
from datetime import datetime, UTC
import pandas as pd

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question
from retrieval.agent import build_agent, run_agent_question

settings = load_settings()

# Minimal dataframe with the columns LocalEmbeddingIndex._build_documents() expects.
# In the real pipeline this comes from ingestion/cleaning.py.
df = pd.DataFrame([{
    "paper_id": "10.1234/example",
    "title": "Retrieval-Augmented Generation for Knowledge-Intensive Tasks",
    "summary": "A survey of RAG techniques combining retrievers with generators.",
    "authors_joined": "Alice Author, Bob Writer",
    "categories_joined": "cs.CL",
    "published": "2024-05-01",
    "abs_url": "https://doi.org/10.1234/example",
    "pdf_url": "",
    "text_for_embedding": "Retrieval-Augmented Generation for Knowledge-Intensive Tasks. "
                          "A survey of RAG techniques combining retrievers with generators.",
}])

# Builds a Chroma collection under data/chroma/ and writes a manifest to settings.paths.embeddings_json
index = LocalEmbeddingIndex.build(df, settings)

# No LLM call — pure vector search + rule-based extraction:
results = index.search("What is RAG?", top_k=1)
print(results[0].title, results[0].score)

answer = answer_question("What is RAG about?", settings=settings, index=index)
print(answer.answer, answer.retrieved_doc_ids)

# Requires a valid LLM credential for settings.llm_provider:
agent = build_agent(settings, index)
print(run_agent_question(agent, "Who wrote the RAG survey paper?"))
```

To reuse a previously built index without re-embedding:

```python
index = LocalEmbeddingIndex.load(settings)  # reads settings.paths.embeddings_json by default
```

Pass `embeddings_output_path=settings.paths.corrupted_embeddings_json` (or `repaired_...`) to
`build()`/`load()` when working with the corrupted/repaired dataset states instead of baseline —
this also determines which Chroma collection name (`papers-baseline` / `-corrupted` / `-repaired`)
is used.
