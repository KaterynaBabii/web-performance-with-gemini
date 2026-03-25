#!/usr/bin/env python3
"""
Run one cross-model advisory round: read diagnostic bundle + task prompt, call
Gemini / OpenAI / Anthropic (if keys set), write llm_comparison/outputs/*.json.

  pip install -r requirements-llm-comparison.txt
  python3 scripts/run_llm_comparison_round.py
  python3 scripts/run_llm_comparison_round.py --dry-run   # no API keys; demo JSON + gold.json

Env (live mode):
  GEMINI_API_KEY or GOOGLE_API_KEY
  OPENAI_API_KEY
  ANTHROPIC_API_KEY
Optional:
  GEMINI_MODEL (default gemini-1.5-flash)
  OPENAI_MODEL (default gpt-4o-mini)
  ANTHROPIC_MODEL (default claude-3-5-sonnet-20241022)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = REPO_ROOT / "llm_comparison" / "bundles" / "baseline_v1" / "diagnostic_bundle.md"
TASK_PATH = REPO_ROOT / "prompts" / "llm_comparison_task.md"
SCHEMA_PATH = REPO_ROOT / "llm_comparison" / "schema" / "model_output.schema.json"
OUT_DIR = REPO_ROOT / "llm_comparison" / "outputs"

PROMPT_VERSION_DEFAULT = "llm_comparison_v1"
BUNDLE_ID_DEFAULT = "baseline_v1"


def load_text(p: Path) -> str:
    if not p.is_file():
        raise FileNotFoundError(p)
    return p.read_text(encoding="utf-8")


def extract_json_object(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("Could not parse JSON object from model response")


def validate_schema(obj: dict) -> None:
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=obj, schema=schema)


def normalize_run(
    obj: dict,
    *,
    raw_text: str,
    run_id: str,
    default_model_id: str,
    prompt_version: str,
    diagnostics_bundle_id: str,
    temperature: float,
) -> dict:
    """Ensure required schema fields; flatten legacy nested model."""
    out = dict(obj)
    nested = out.pop("model", None)
    if isinstance(nested, dict) and "model_id" not in out:
        mid = nested.get("model_id") or nested.get("id")
        if mid:
            out["model_id"] = str(mid)
    out.setdefault("model_id", default_model_id)
    out["run_id"] = run_id
    out.setdefault("prompt_version", prompt_version)
    out.setdefault("diagnostics_bundle_id", diagnostics_bundle_id)
    out.setdefault("temperature", temperature)
    out["raw_text"] = (out.get("raw_text") or raw_text or "")[:500000]
    for rec in out.get("recommendations") or []:
        if "primary_category" not in rec and "category" in rec:
            rec["primary_category"] = rec.pop("category")
        rec.setdefault("detail", rec.get("title", ""))
    return out


def call_gemini(user_prompt: str) -> tuple[str, str]:
    import google.generativeai as genai

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY not set")
    genai.configure(api_key=key)
    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    resp = model.generate_content(user_prompt)
    text = (resp.text or "").strip()
    return text, model_name


def call_openai(user_prompt: str) -> tuple[str, str]:
    from openai import OpenAI

    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.2,
    )
    text = (r.choices[0].message.content or "").strip()
    return text, model


def call_anthropic(user_prompt: str) -> tuple[str, str]:
    import anthropic

    client = anthropic.Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    msg = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[{"role": "user", "content": user_prompt}],
    )
    parts = msg.content or []
    text = "".join(getattr(b, "text", str(b)) for b in parts).strip()
    return text, model


def build_user_prompt(bundle_md: str, task_md: str) -> str:
    return (
        task_md.strip()
        + "\n\n---\n\n## Attached diagnostic bundle (read carefully)\n\n"
        + bundle_md.strip()
        + "\n\n---\n\nReturn **only** one JSON object matching the schema. No markdown outside the JSON."
    )


def dry_run_payloads(
    run_gemini: str,
    run_gpt: str,
    run_claude: str,
) -> tuple[dict[str, dict], dict]:
    """Schema-compliant outputs + gold.json for analyze_llm_advisory_comparison.py."""
    base_kw = dict(
        prompt_version=PROMPT_VERSION_DEFAULT,
        diagnostics_bundle_id=BUNDLE_ID_DEFAULT,
        temperature=0.2,
        max_tokens=4096,
        timestamp_utc="2025-03-24T12:00:00Z",
    )

    gem = {
        "run_id": run_gemini,
        "model_id": "gemini-dry-run",
        **base_kw,
        "raw_text": "dry-run synthetic",
        "recommendations": [
            {
                "id": "R1",
                "title": "Add GIN / trigram index for product search",
                "detail": "ILIKE on name/description; use pg_trgm GIN or FTS.",
                "primary_category": "indexing",
                "evidence_citations": ["code:products", "bundle:search"],
                "targets": {"tables": ["products"], "routes": ["/products"]},
            },
            {
                "id": "R2",
                "title": "Batch dashboard order_items",
                "detail": "Replace N+1 with one JOIN or batched IN query.",
                "primary_category": "query_rewrite",
                "evidence_citations": ["code:dashboard"],
                "targets": {"routes": ["/users/:id/dashboard"]},
            },
            {
                "id": "R3",
                "title": "Redis cache for recommendations",
                "detail": "Cache aggregate recommendation query with TTL.",
                "primary_category": "caching",
                "evidence_citations": ["code:recommendations"],
                "targets": {"routes": ["/recommendations/:userId"]},
            },
        ],
    }
    gpt = {
        "run_id": run_gpt,
        "model_id": "gpt-dry-run",
        **base_kw,
        "raw_text": "dry-run synthetic",
        "recommendations": [
            {
                "id": "R1",
                "title": "Trigram GIN on products for ILIKE",
                "detail": "Same family as G1; wording variant.",
                "primary_category": "indexing",
                "evidence_citations": ["code:products"],
                "targets": {"tables": ["products"]},
            },
            {
                "id": "R2",
                "title": "Single-query dashboard with JOINs",
                "detail": "Collapse per-order loops into one round-trip.",
                "primary_category": "query_rewrite",
                "evidence_citations": ["code:dashboard"],
            },
            {
                "id": "R4",
                "title": "Wrap checkout in a transaction",
                "detail": "BEGIN/COMMIT around order + order_items inserts.",
                "primary_category": "transaction_handling",
                "evidence_citations": ["code:checkout"],
                "targets": {"routes": ["/checkout"]},
            },
        ],
    }
    claude = {
        "run_id": run_claude,
        "model_id": "claude-dry-run",
        **base_kw,
        "raw_text": "dry-run synthetic",
        "recommendations": [
            {
                "id": "R1",
                "title": "Full-text or trigram index for search",
                "detail": "Avoid sequential scan on ILIKE.",
                "primary_category": "indexing",
                "evidence_citations": ["bundle:search"],
            },
            {
                "id": "R2",
                "title": "Batched items load for dashboard",
                "detail": "Reduce round-trips for order_items.",
                "primary_category": "query_rewrite",
            },
            {
                "id": "R5",
                "title": "Connection pool sizing under load",
                "detail": "Tune pool vs. DB max_connections from Locust saturation.",
                "primary_category": "bottleneck_diagnosis",
                "risk_notes": "Verify with pool metrics, not guesswork.",
            },
        ],
    }

    gold = {
        "gold_id": "gold-dry-run-demo",
        "bundle_id": BUNDLE_ID_DEFAULT,
        "items": [
            {
                "id": "G1",
                "canonical_key": "gin_fts_products",
                "primary_category": "indexing",
                "description": "Index product search path (GIN/trigram/FTS)",
            },
            {
                "id": "G2",
                "canonical_key": "dashboard_n1_elimination",
                "primary_category": "query_rewrite",
                "description": "Remove N+1 on dashboard",
            },
            {
                "id": "G3",
                "canonical_key": "recommendations_cache_ttl",
                "primary_category": "caching",
                "description": "Cache recommendations with TTL",
            },
            {
                "id": "G4",
                "canonical_key": "checkout_transaction",
                "primary_category": "transaction_handling",
                "description": "Atomic checkout (transaction)",
            },
            {
                "id": "G5",
                "canonical_key": "pool_saturation",
                "primary_category": "bottleneck_diagnosis",
                "description": "Diagnose pool/connection saturation",
            },
        ],
        "model_item_labels": [
            {
                "model_run_id": run_gemini,
                "item_id": "R1",
                "maps_to_gold_id": "G1",
                "match_type": "full",
                "invalid_unsafe": False,
                "quality": {
                    "correctness": 5,
                    "actionability": 5,
                    "novelty": 4,
                    "safety": 5,
                    "effort": 4,
                },
            },
            {
                "model_run_id": run_gemini,
                "item_id": "R2",
                "maps_to_gold_id": "G2",
                "match_type": "full",
                "invalid_unsafe": False,
                "quality": {"correctness": 4, "actionability": 4, "novelty": 3, "safety": 5, "effort": 4},
            },
            {
                "model_run_id": run_gemini,
                "item_id": "R3",
                "maps_to_gold_id": "G3",
                "match_type": "full",
                "invalid_unsafe": False,
                "quality": {"correctness": 5, "actionability": 4, "novelty": 4, "safety": 4, "effort": 3},
            },
            {
                "model_run_id": run_gpt,
                "item_id": "R1",
                "maps_to_gold_id": "G1",
                "match_type": "full",
                "invalid_unsafe": False,
                "quality": {"correctness": 5, "actionability": 5, "novelty": 3, "safety": 5, "effort": 4},
            },
            {
                "model_run_id": run_gpt,
                "item_id": "R2",
                "maps_to_gold_id": "G2",
                "match_type": "full",
                "invalid_unsafe": False,
                "quality": {"correctness": 4, "actionability": 4, "novelty": 3, "safety": 5, "effort": 4},
            },
            {
                "model_run_id": run_gpt,
                "item_id": "R4",
                "maps_to_gold_id": "G4",
                "match_type": "full",
                "invalid_unsafe": False,
                "quality": {"correctness": 5, "actionability": 5, "novelty": 3, "safety": 5, "effort": 3},
            },
            {
                "model_run_id": run_claude,
                "item_id": "R1",
                "maps_to_gold_id": "G1",
                "match_type": "full",
                "invalid_unsafe": False,
                "quality": {"correctness": 5, "actionability": 4, "novelty": 3, "safety": 5, "effort": 4},
            },
            {
                "model_run_id": run_claude,
                "item_id": "R2",
                "maps_to_gold_id": "G2",
                "match_type": "full",
                "invalid_unsafe": False,
                "quality": {"correctness": 4, "actionability": 4, "novelty": 3, "safety": 5, "effort": 4},
            },
            {
                "model_run_id": run_claude,
                "item_id": "R5",
                "maps_to_gold_id": "G5",
                "match_type": "full",
                "invalid_unsafe": False,
                "quality": {"correctness": 4, "actionability": 3, "novelty": 4, "safety": 5, "effort": 3},
            },
        ],
    }

    files = {"gemini.json": gem, "gpt4.json": gpt, "claude.json": claude}
    return files, gold


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Write synthetic JSON without API calls")
    ap.add_argument("--no-validate", action="store_true", help="Skip jsonschema validation if installed")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pv = os.environ.get("LLM_COMPARISON_PROMPT_VERSION", PROMPT_VERSION_DEFAULT)
    bid = os.environ.get("LLM_COMPARISON_BUNDLE_ID", BUNDLE_ID_DEFAULT)
    temp = float(os.environ.get("LLM_COMPARISON_TEMPERATURE", "0.2"))

    if args.dry_run:
        rid_g, rid_o, rid_c = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        files, gold = dry_run_payloads(rid_g, rid_o, rid_c)
        for name, obj in files.items():
            if not args.no_validate:
                validate_schema(obj)
            (OUT_DIR / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
        gold_path = OUT_DIR / "gold.json"
        gold_path.write_text(json.dumps(gold, indent=2) + "\n", encoding="utf-8")
        print(f"Dry-run wrote {OUT_DIR}/gemini.json, gpt4.json, claude.json, gold.json")
        print(f"  run_ids: gemini={rid_g} gpt={rid_o} claude={rid_c}")
        return 0

    bundle = load_text(BUNDLE_PATH)
    task = load_text(TASK_PATH)
    user_prompt = build_user_prompt(bundle, task)

    callers: list[tuple[str, str, object]] = [
        ("gemini.json", "gemini", call_gemini),
        ("gpt4.json", "openai", call_openai),
        ("claude.json", "anthropic", call_anthropic),
    ]

    for out_name, _prov, fn in callers:
        run_id = str(uuid.uuid4())
        raw, api_model = fn(user_prompt)
        obj = extract_json_object(raw)
        obj = normalize_run(
            obj,
            raw_text=raw,
            run_id=run_id,
            default_model_id=api_model,
            prompt_version=pv,
            diagnostics_bundle_id=bid,
            temperature=temp,
        )
        if not args.no_validate:
            validate_schema(obj)
        (OUT_DIR / out_name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {OUT_DIR / out_name} run_id={run_id} model_id={obj['model_id']}")

    print("Done. Add llm_comparison/outputs/gold.json (expert, blinded) and optional labels CSV, then run analyze_llm_advisory_comparison.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)
