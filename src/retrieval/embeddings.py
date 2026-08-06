from __future__ import annotations

from functools import lru_cache
import hashlib
import math
import re

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from openai import APIConnectionError, APITimeoutError
from sentence_transformers import SentenceTransformer

from core.config import Settings


_FALLBACK_DIMENSIONS = 384
_OPENAI_FALLBACK_DIMENSIONS = 1536
_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer | None:
    """Load only from the local Hugging Face cache.

    Pipeline execution must remain deterministic and usable on lab machines
    whose firewall blocks huggingface.co. A missing cache is handled by the
    local hashing fallback below instead of triggering network retries.
    """
    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except Exception as exc:
        print(
            "WARNING: Local embedding model cache is unavailable; "
            f"using deterministic {_FALLBACK_DIMENSIONS}d hashing embeddings ({exc})."
        )
        return None


def _hash_embedding(text: str, dimensions: int = _FALLBACK_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    tokens = _TOKEN_RE.findall(text.lower())
    features = tokens + [f"{left}::{right}" for left, right in zip(tokens, tokens[1:])]
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


class ConfiguredEmbeddings(Embeddings):
    """Embedding adapter selected independently from the chat provider."""

    def __init__(self, settings: Settings, *, force_local_fallback: bool = False):
        self.provider = settings.embedding_provider.strip().lower()
        self.model_name = settings.embedding_model
        self.openai_model: OpenAIEmbeddings | None = None
        self.model: SentenceTransformer | None = None
        self.local_fallback = force_local_fallback
        self.actual_provider = "local-hash-fallback" if force_local_fallback else self.provider

        if self.provider == "openai":
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai.")
            if not force_local_fallback:
                self.openai_model = OpenAIEmbeddings(
                    model=self.model_name,
                    api_key=settings.openai_api_key,
                    request_timeout=20,
                    max_retries=0,
                )
        elif self.provider in {"local", "sentence_transformers", "huggingface"}:
            self.model = _load_model(self.model_name)
        else:
            raise ValueError("Unsupported EMBEDDING_PROVIDER. Expected: openai or local.")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.openai_model is not None and not self.local_fallback:
            try:
                embeddings = self.openai_model.embed_documents(texts)
                self.actual_provider = "openai"
                return embeddings
            except (APIConnectionError, APITimeoutError) as exc:
                self.local_fallback = True
                self.actual_provider = "local-hash-fallback"
                print(
                    "WARNING: OpenAI embeddings are unreachable; using a consistent "
                    f"{_OPENAI_FALLBACK_DIMENSIONS}d local fallback for this collection ({exc})."
                )
        if self.provider == "openai" or self.local_fallback:
            return [_hash_embedding(text, _OPENAI_FALLBACK_DIMENSIONS) for text in texts]
        if self.model is None:
            return [_hash_embedding(text) for text in texts]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if self.openai_model is not None and not self.local_fallback:
            try:
                return self.openai_model.embed_query(text)
            except (APIConnectionError, APITimeoutError) as exc:
                self.local_fallback = True
                self.actual_provider = "local-hash-fallback"
                print(f"WARNING: OpenAI query embedding unavailable; using local fallback ({exc}).")
        if self.provider == "openai" or self.local_fallback:
            return _hash_embedding(text, _OPENAI_FALLBACK_DIMENSIONS)
        if self.model is None:
            return _hash_embedding(text)
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()


MiniLMEmbeddings = ConfiguredEmbeddings
