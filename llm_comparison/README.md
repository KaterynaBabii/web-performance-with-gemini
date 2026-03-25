# Cross-model LLM comparison (offline performance advisory)

Reproducible materials for a **comparison of Gemini, GPT-4, and Claude** as *offline* advisors (not runtime controllers), focused on measured recommendation quality and overlap.

## Recommended strategy

Use **Option B (lightweight)** for a minimal publishable protocol: one **frozen diagnostic bundle**, **identical prompt** (`prompts/llm_comparison_task.md`), **structured JSON** outputs from each API, **one expert gold set** built *before* viewing model outputs, then blinded (or sequential) scoring. Report **category counts**, **pairwise Jaccard** on deduplicated keys, **precision@gold**, and **invalid/unsafe rate**.

Add **Option A (implementation yield)** only if you can allocate a **fixed engineering budget per model** (e.g., 8 h) on the same codebase snapshot.

## 1) Full methodology (Option A)

### 1.1 Freeze inputs

| ID | Artifact |
|----|-----------|
| D | Representative code: search, dashboard, recommendations, checkout (baseline paths). |
| E1–E3 | `EXPLAIN (ANALYZE, BUFFERS)` for search, dashboard-style query, checkout-related query. |
| S | `pg_stat_statements` top-N by total time (same N for all models). |
| L | Slow-query log excerpt (same time window as a reference Locust run). |
| W | Locust summary: RPS, percentiles, errors (e.g. one steady-state run @300 users). |
| P | Prompt template: `prompts/llm_comparison_task.md` (version in JSON `prompt_version`). |

Store copies under `llm_comparison/bundles/<bundle_id>/` (create per study; not committed if sensitive—use `bundles/.gitkeep` + README only).

### 1.2 Models (document exact API strings)

- Gemini: e.g. `gemini-2.0-flash` or `gemini-2.5-pro-preview-05-06`
- GPT-4: e.g. `gpt-4o-2024-08-06`
- Claude: e.g. `claude-3-5-sonnet-20241022`

**Fairness:** same `temperature` (0–0.2), same `max_tokens`, **no** web search unless enabled for **all** three.

### 1.3 Procedure

1. Run each model once (or k=3 with low T—then report variance in supplement).
2. Save raw response + parsed JSON per `schema/model_output.schema.json`.
3. Expert(s) build **gold** list `gold.json` **without** seeing model outputs (reference standard).
4. Map each model item → gold: `full | partial | none`; flag `invalid_unsafe`.
5. **Blinding:** shuffle items as IDs `M1..M3` for quality Likert ratings (1–5): correctness, actionability, novelty/relevance, safety, implementation effort (5 = low effort).
6. **Optional (A):** Per model, implement top-5 under fixed hours; Locust before/after @ one load, 3 reps.

### 1.4 Categories (primary label per recommendation)

`indexing` · `query_rewrite` · `caching` · `batching` · `transaction_handling` · `bottleneck_diagnosis` · `invalid_unsafe`

### 1.5 Scoring rubric (Likert anchors)

| Score | Correctness / actionability |
|-------|-----------------------------|
| 5 | Concrete DDL or rewrite tied to named tables/routes; cache TTL/invalidation considered if relevant. |
| 3 | Right family (e.g. “add index”) but vague or wrong object. |
| 1 | Generic advice unrelated to bundle evidence. |

**Invalid/unsafe:** wrong SQL dialect, nonexistent objects, destructive prod change without staging—count in `invalid_unsafe` and in separate invalid table.

### 1.6 Metrics

- **Jaccard** on canonical keys between model pairs.
- **Precision@G:** full matches / total model items (per model).
- **Invalid rate:** invalid items / total.
- **Implementation yield (A only):** Δp95, ΔRPS under fixed budget.

## 2) Lightweight methodology (Option B)

Same bundle + prompt + JSON; **one** expert gold set; **no** implementation arm—add qualitative paragraph on verbosity/SQL style. State *n*=1 bundle limitation in Limitations.

## 3) Table schemas

| Table | Rows | Cols (core) |
|-------|------|-------------|
| Model × category | 3 models | counts per category + total |
| Pairwise Jaccard | 3 pairs | J |
| Model × human agreement | 3 models | n, P@G, partial, none, invalid_rate, mean Likerts |
| Model × invalid | variable | model_id, item_id, title, note |
| Model × yield (A) | 3 models | hours, n_impl, Δp95, ΔRPS |

## 4) Files in this directory

| Path | Role |
|------|------|
| `schema/model_output.schema.json` | JSON Schema for API outputs |
| `examples/gemini.example.json` | Minimal valid example |
| `examples/gold.example.json` | Gold + optional `model_item_labels` |
| `../scripts/analyze_llm_advisory_comparison.py` | CSV analytics |

## 5) Analysis

```bash
python3 scripts/analyze_llm_advisory_comparison.py \
  --models llm_comparison/outputs/gemini.json llm_comparison/outputs/gpt4.json llm_comparison/outputs/claude.json \
  --gold llm_comparison/outputs/gold.json \
  --outdir llm_comparison/analysis_out/
```

## 6) Summary one-liner

*Under identical diagnostic inputs and prompting, we report recommendation category distributions, pairwise overlap (Jaccard), precision against an expert-derived gold set, and invalid-suggestion rates for Gemini, GPT-4, and Claude as offline performance advisors; we do not claim universal model-agnostic behavior without broader bundles and optional controlled implementation.*

## 7) Relation to repo prompts

The task text for models should extend `prompts/perf_engineer_prompt.md` framing with **`prompts/llm_comparison_task.md`** (JSON-only output requirement).
