"""Input loading utilities for recommendations and scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def _ensure_id(source: str, idx: int) -> str:
    return f"{source}_{idx:03d}"


def load_recommendations(path: Path, source: str) -> list[dict]:
    """
    Load recommendations from JSON or text.
    JSON supports either a list or {"recommendations": [...]}.
    Text uses one recommendation per line.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "recommendations" in payload:
            items = payload["recommendations"]
        elif isinstance(payload, list):
            items = payload
        else:
            raise ValueError(f"Unsupported JSON shape in {path}")
        out = []
        for i, item in enumerate(items, start=1):
            rec_id = item.get("id") or _ensure_id(source, i)
            out.append(
                {
                    "recommendation_id": str(rec_id),
                    "source": source,
                    "raw_text": str(item.get("text") or item.get("raw_text") or "").strip(),
                    "raw_category": item.get("category"),
                    "artifact_refs": item.get("artifact_refs"),
                }
            )
        return out

    if path.suffix.lower() in {".txt", ".md"}:
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
        out = []
        for i, ln in enumerate([l for l in lines if l], start=1):
            out.append(
                {
                    "recommendation_id": _ensure_id(source, i),
                    "source": source,
                    "raw_text": ln,
                    "raw_category": None,
                    "artifact_refs": None,
                }
            )
        return out

    raise ValueError(f"Unsupported input type: {path}")


def discover_input_files(inputs_dir: Path) -> dict[str, Path]:
    """
    Discover input files using basename as the source id.
    e.g., gemini.json -> source "gemini".
    """
    sources: dict[str, Path] = {}
    for path in inputs_dir.iterdir():
        if path.is_dir():
            continue
        if path.suffix.lower() not in {".json", ".txt", ".md"}:
            continue
        source = path.stem.lower()
        sources[source] = path
    return sources


def write_csv(path: Path, rows: Iterable[dict], columns: list[str]) -> None:
    import pandas as pd

    df = pd.DataFrame(rows, columns=columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
