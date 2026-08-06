# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A student lab: a small RAG data pipeline (Crossref ingestion → cleaning → embedding/ChromaDB →
retrieval agent → evaluation → data-quality/freshness observability → deliberate data corruption →
repair → before/after comparison). Most of `src/` is intentionally stubbed with
`TODO(student)` docstrings and `raise NotImplementedError(...)` — that is the expected starting
state, not a bug. `src/retrieval/` (embeddings, index, llm, agent, qa) is reference code that is
already implemented and should generally be read, not rewritten.

Full task spec: [Guide.md](Guide.md) (step-by-step) and [Rubric.md](Rubric.md) (grading). Env/setup
steps live in [README.md](README.md).

## Commands

Install (editable install is required — `pip install -r requirements.txt` alone installs
dependencies but not the `src/` package, causing `No module named 'pipelines'` etc.):

```bash
uv sync                      # preferred, uses uv.lock
# or
python -m pip install -e .
```

Find remaining student work:

```bash
rg -n "TODO\(student\)|NotImplementedError" src
```

Run the two pipelines (must run phase1 before corruption_flow — the latter reads baseline
artifacts):

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

Env config: copy `.env.example` to `.env` (see README §3). Key vars: `LLM_PROVIDER` /
`LLM_MODEL` + the matching provider API key, `REFRESH_SOURCE=1` / `REFRESH_TEST_SET=1` to force
re-fetching/regenerating instead of reusing cached artifacts under `data/`, `RUN_RAGAS=1` to
enable the (slow) ragas metrics pass in evaluation.

No lint config or test suite exists yet in this repo; `pytest` is available as a dev dependency
(`uv sync --extra dev`) if you add tests.

## Architecture

**Path/settings pattern.** `core/config.py:load_settings()` is the single source of truth: it
returns a frozen `Settings` dataclass containing a nested frozen `Paths` dataclass with every
input/output file path under `data/`. Every module takes `settings: Settings` and reads paths off
`settings.paths.*` rather than constructing paths itself — when adding a new artifact, add its
path to `Paths` in `config.py` first.

**Three parallel dataset states.** The lab's core deliverable is comparing baseline vs. corrupted
vs. repaired data. Each state has its own clean CSV/JSON, its own embeddings manifest JSON, and
its own ChromaDB collection name (`papers-baseline` / `papers-corrupted` / `papers-repaired`,
defined in `Settings`) — all sharing one Chroma persist directory (`data/chroma`). Anything working
with embeddings/index must pass the *state-specific* path/collection through, not the baseline
default.

**Import root.** `pyproject.toml` sets `package-dir = {"" = "src"}`, so after an editable install,
top-level imports are `from core.config import ...`, `from ingestion.crossref import ...`, etc.
(not `from src.core...`). This only works once the package is pip/uv-installed — running scripts
without an editable install breaks these imports.

**LLM provider abstraction.** `retrieval/llm.py:build_llm()` dispatches on
`core.config.normalized_provider()` to construct one of `ChatGoogleGenerativeAI` / `ChatOpenAI` /
`ChatAnthropic` / `ChatOllama` / OpenAI-compatible-custom via langchain, and
`require_llm_credentials()` validates the right key/URL is present for the selected provider
before any call is made. Add a new provider by extending both functions plus `Settings`.

**Retrieval stack.** `retrieval/embeddings.py:MiniLMEmbeddings` wraps
`sentence-transformers/all-MiniLM-L6-v2` as a langchain `Embeddings` (model instance cached via
`lru_cache`). `retrieval/index.py:LocalEmbeddingIndex` owns a `chromadb.PersistentClient`
collection: `.build()` embeds a cleaned dataframe and writes both the Chroma collection and a JSON
manifest (`documents` + `metadata`) to the relevant `*_embeddings.json` path; `.load()` rehydrates
an index from that manifest without re-embedding. `.search()` does top-k cosine similarity;
`.lookup()` does exact match on `paper_id` or `title` — both `retrieval/qa.py:answer_question()`
and the agent tools in `retrieval/agent.py` use `lookup()` first (for quoted-title questions) then
fall back to/merge with `search()`.

**Agent.** `retrieval/agent.py:build_agent()` builds a langchain `create_agent` with two tools
(`semantic_search_papers`, `lookup_paper`) closed over a `LocalEmbeddingIndex` instance, backed by
whatever `build_llm()` returns for the configured provider.

**Evaluation.** `evaluation/metrics.py:evaluate_pipeline()` runs every item in a test-set JSON
through `answer_question()`, then scores each answer three ways: token-F1 against
`ground_truth`, retrieval hit rate against `ground_truth_doc_ids`, and an LLM-as-judge
(`JudgeVerdict` structured output via `.with_structured_output`) that falls back to a token-F1-based
heuristic score if the LLM call throws. An optional ragas pass (`answer_relevancy`,
`context_precision`, `context_recall`, `faithfulness`) is gated behind `RUN_RAGAS=1` since it's
slow and requires extra setup (there's a small `sys.modules` shim for a ragas/langchain_community
import quirk — leave it as-is).

**Pipeline orchestration.** `script/run_phase1.py` and `script/run_corruption_flow.py` are one-line
wrappers calling `pipelines.phase1.main()` / `pipelines.corruption_flow.main()`. All actual
orchestration (fetch → clean → build index → build/load test set → evaluate → quality/freshness
checks → markdown report, and then corrupt → re-evaluate → repair → re-evaluate → comparison
report) belongs in those two `pipelines/*.py` files, which are themselves student stubs — they are
the modules that wire every other module together, so implement them last, after the pieces they
call (`ingestion/`, `evaluation/testset.py`, `observability/`) exist.
