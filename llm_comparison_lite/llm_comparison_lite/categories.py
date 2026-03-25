"""Normalize free-text categories to canonical labels for fair counting and set overlap."""

from __future__ import annotations

# Map lowercased/aliased labels → canonical name used in tables
CATEGORY_ALIASES: dict[str, str] = {
    # indexing family
    "index": "indexing",
    "indexing": "indexing",
    "indexes": "indexing",
    "db_index": "indexing",
    "gin": "indexing",
    "fts": "indexing",
    "full_text": "indexing",
    # query shape
    "query": "query_rewrite",
    "query_rewrite": "query_rewrite",
    "query optimization": "query_rewrite",
    "sql": "query_rewrite",
    "n+1": "query_rewrite",
    "n1": "query_rewrite",
    "batching": "batching",
    "batch": "batching",
    # cache
    "cache": "caching",
    "caching": "caching",
    "redis": "caching",
    # transactions
    "transaction": "transaction_handling",
    "transactions": "transaction_handling",
    "transaction_handling": "transaction_handling",
    "atomicity": "transaction_handling",
    # diagnosis / ops
    "bottleneck": "bottleneck_diagnosis",
    "bottlenecks": "bottleneck_diagnosis",
    "bottleneck_diagnosis": "bottleneck_diagnosis",
    "pool": "bottleneck_diagnosis",
    "connection_pool": "bottleneck_diagnosis",
    "monitoring": "bottleneck_diagnosis",
    # bad outputs
    "invalid": "invalid_unsafe",
    "unsafe": "invalid_unsafe",
    "hallucination": "invalid_unsafe",
    "hallucinated": "invalid_unsafe",
    "invalid_unsafe": "invalid_unsafe",
}

# Stable ordering for breakdown tables
CANONICAL_CATEGORIES = [
    "indexing",
    "query_rewrite",
    "caching",
    "batching",
    "transaction_handling",
    "bottleneck_diagnosis",
    "invalid_unsafe",
    "other",
]


def normalize_category(raw: str) -> str:
    """
    Map a category string to a canonical bucket.
    Unrecognized labels are mapped to \"other\" (original stays in \"category\").
    """
    if raw is None:
        return "other"
    key = str(raw).lower().strip()
    if key in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key]
    alt = key.replace(" ", "_").replace("-", "_")
    if alt in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[alt]
    if key in CANONICAL_CATEGORIES or alt in CANONICAL_CATEGORIES:
        return alt if alt in CANONICAL_CATEGORIES else key
    return "other"


def attach_normalized_category(rows: list[dict]) -> None:
    """Mutate rows in place: set \"category_normalized\"."""
    for r in rows:
        r["category_normalized"] = normalize_category(r.get("category", ""))
