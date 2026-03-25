# Lightweight LLM comparison (Python)

**This is the only Markdown document for the `llm_comparison_lite` mini-project** (instructions, schema, metrics, example tables). Do not add a separate `README.md` here.

| Requirement | Where it lives |
|-------------|----------------|
| Inputs: `gemini.json`, `gpt4.json`, `claude.json`, `human.json` | `data/` (see §1) |
| Fields: `endpoint`, `raw_text`, `category`, `accepted_by_human`, `invalid_or_hallucinated`, `safety_risk` | Validated in `llm_comparison_lite/io.py` |
| Load → normalize categories → per-model metrics | `run_analysis.py` + `categories.py` + `metrics.py` |
| Outputs: `summary.csv`, `pairwise_overlap.csv`, `category_breakdown.csv` | `outputs/` (after run) |
| Publication-style console text | `report.py` |
| **Gemini vs human (paper reviewer table)** | `run_paper_overlap.py` → `paper_overlap_summary.csv`, `table_gemini_human_overlap.tex` (see `docs/GEMINI_VS_HUMAN_ENGINEER_COMPARISON.md`) |
| Dependencies | stdlib + **pandas**, **numpy**, **matplotlib** only (`requirements.txt`) |

---

## 1. Input format

Place four files in `data/` (names are fixed in code):

| File | Role |
|------|------|
| `gemini.json` | Recommendations from Gemini |
| `gpt4.json` | Recommendations from GPT-4-class model |
| `claude.json` | Recommendations from Claude |
| `human.json` | Expert / gold list (reference set for Jaccard “agreement”) |

Each file is a **JSON array** of objects (or a single object with a `"recommendations"` array). Every item **must** include:

| Field | Type | Notes |
|-------|------|--------|
| `endpoint` | string | e.g. `GET /products` (used in overlap keys) |
| `raw_text` | string | Full suggestion text |
| `category` | string | Free text; normalized internally (see §4) |
| `accepted_by_human` | boolean | Human judged this item acceptable |
| `invalid_or_hallucinated` | boolean | Human judged invalid / hallucinated |
| `safety_risk` | string | One of `low`, `medium`, `high` |

Example minimal object:

```json
{
  "endpoint": "GET /products",
  "raw_text": "Add a trigram GIN index for ILIKE search.",
  "category": "indexing",
  "accepted_by_human": true,
  "invalid_or_hallucinated": false,
  "safety_risk": "low"
}
```

Dummy datasets for a quick dry run live under `data/*.json`.

---

## 2. Install and run

From **`llm_comparison_lite/`** (this directory):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python3 -m pip install -r requirements.txt
```

On macOS, if `pip` is not found, always use **`python3 -m pip`** (same as above).

**Full pipeline** (CSV + console report):

```bash
python3 run_analysis.py --data-dir data --out-dir outputs
```

**Gemini vs independent human engineer** (overlap / agreement table for revision; uses only `gemini.json` + `human.json`):

```bash
python3 run_paper_overlap.py --data-dir data --out-dir outputs
```

**Refresh Markdown tables** (prints pipe tables to stdout—paste into the “Example output” section below if your data changed):

```bash
python3 run_analysis.py --data-dir data --emit-markdown-only
```

**Quiet file run** (no long console text; still writes CSV/TeX):

```bash
python3 run_analysis.py --data-dir data --out-dir outputs --quiet
```

---

## 3. Outputs

| Artifact | Description |
|----------|-------------|
| `outputs/summary.csv` | Per-LLM totals, rates, human Jaccard, mean Jaccard vs other LLMs |
| `outputs/pairwise_overlap.csv` | Pairwise Jaccard between `gemini`, `gpt4`, `claude` |
| `outputs/category_breakdown.csv` | Counts and rates by `model` × normalized `category` (includes `human`) |

`\input{...}` the `.tex` files from your manuscript or copy rows into your own table environment.

---

## 4. Metrics (definitions)

- **total recommendations** — row count in each model file (`gemini` / `gpt4` / `claude` only in `summary.csv`).
- **accepted recommendations** — count of `accepted_by_human == true`.
- **acceptance rate** — accepted / total.
- **invalid suggestion rate** — `invalid_or_hallucinated == true` / total.
- **hallucination rate** — same numerator/denominator as invalid rate here (single boolean in the schema; both columns are reported for paper wording).
- **safety_high_risk_rate** — fraction with `safety_risk == "high"`.
- **agreement with human expert** — **Jaccard index** between the model’s set of keys and the human file’s set of keys. Each key is `endpoint_lowercase || category_normalized` (delimiter `||`).
- **Jaccard overlap with other models** — pairwise Jaccard on the same keys between LLMs; `summary.csv` includes **mean** Jaccard vs the *other two* models (`mean_jaccard_vs_other_llms`). Full pairs are in `pairwise_overlap.csv`.

**Category normalization** maps aliases (e.g. `redis`, `n+1`, `FTS`, `hallucination`) into canonical buckets such as `indexing`, `query_rewrite`, `caching`, `batching`, `transaction_handling`, `bottleneck_diagnosis`, `invalid_unsafe`, or `other`. See `llm_comparison_lite/categories.py`.

---

## 5. Project layout

```
llm_comparison_lite/
  LIGHTWEIGHT_COMPARISON.md    ← this file (only Markdown doc for this mini-project)
  requirements.txt
  run_analysis.py              ← CLI entrypoint
  data/
    gemini.json
    gpt4.json
    claude.json
    human.json
  llm_comparison_lite/         ← importable package
    __init__.py
    io.py                      # load + validate JSON
    categories.py              # normalize labels
    metrics.py                 # Jaccard, summaries, breakdown
    plots.py                   # optional matplotlib
    report.py                  # console + Markdown fragments
  outputs/                     # generated (gitignored except .gitkeep)
```
