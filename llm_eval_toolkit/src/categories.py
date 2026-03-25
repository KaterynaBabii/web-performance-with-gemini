"""Category normalization and light keyword inference."""

from __future__ import annotations

import re
from typing import Iterable


CANONICAL_CATEGORIES = [
    "indexing",
    "query_rewrite",
    "n_plus_one_elimination",
    "caching",
    "transaction_or_batching",
    "invalid_unsafe",
    "other",
]

ALIAS_TO_CANONICAL = {
    # indexing
    "index": "indexing",
    "indexes": "indexing",
    "indexing": "indexing",
    "gin": "indexing",
    "gist": "indexing",
    "btree": "indexing",
    "fts": "indexing",
    "full_text_search": "indexing",
    "trigram": "indexing",
    # query rewrite
    "query": "query_rewrite",
    "query_rewrite": "query_rewrite",
    "rewrite": "query_rewrite",
    "join": "query_rewrite",
    "subquery": "query_rewrite",
    # n+1 elimination
    "n+1": "n_plus_one_elimination",
    "n1": "n_plus_one_elimination",
    "n_plus_one": "n_plus_one_elimination",
    "batching": "n_plus_one_elimination",
    "batch": "n_plus_one_elimination",
    "dataloader": "n_plus_one_elimination",
    # caching
    "cache": "caching",
    "caching": "caching",
    "redis": "caching",
    "memoize": "caching",
    "ttl": "caching",
    # transaction or batching
    "transaction": "transaction_or_batching",
    "transactions": "transaction_or_batching",
    "commit": "transaction_or_batching",
    "rollback": "transaction_or_batching",
    "atomicity": "transaction_or_batching",
    # invalid
    "invalid": "invalid_unsafe",
    "unsafe": "invalid_unsafe",
    "hallucination": "invalid_unsafe",
    "hallucinated": "invalid_unsafe",
    "invalid_unsafe": "invalid_unsafe",
}

_SEP_RE = re.compile(r"[,\|;/]+")


def _normalize_token(token: str) -> str:
    key = token.strip().lower().replace("-", "_").replace(" ", "_")
    return ALIAS_TO_CANONICAL.get(key, key)


def normalize_categories(raw: str | Iterable[str] | None) -> list[str]:
    if raw is None:
        return ["other"]
    if isinstance(raw, str):
        parts = [p for p in _SEP_RE.split(raw) if p.strip()]
    else:
        parts = [str(p) for p in raw if str(p).strip()]
    normalized = [_normalize_token(p) for p in parts]
    normalized = [n for n in normalized if n in CANONICAL_CATEGORIES]
    return sorted(set(normalized)) if normalized else ["other"]


def infer_categories_from_text(text: str) -> list[str]:
    """Lightweight keyword-based inference when no category is provided."""
    if not text:
        return ["other"]
    t = text.lower()
    found = set()

    if any(k in t for k in ["index", "gin", "gist", "btree", "trigram", "fts", "full text"]):
        found.add("indexing")
    if any(k in t for k in ["rewrite", "join", "subquery", "plan", "explain"]):
        found.add("query_rewrite")
    if any(k in t for k in ["n+1", "n plus one", "batch", "dataloader", "chatty"]):
        found.add("n_plus_one_elimination")
    if any(k in t for k in ["cache", "redis", "ttl", "memoize"]):
        found.add("caching")
    if any(k in t for k in ["transaction", "commit", "rollback", "atomic"]):
        found.add("transaction_or_batching")
    if any(k in t for k in ["hallucination", "unsafe", "invalid", "nonexistent"]):
        found.add("invalid_unsafe")

    return sorted(found) if found else ["other"]
