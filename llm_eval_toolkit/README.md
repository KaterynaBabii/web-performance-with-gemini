# LLM Recommendation Evaluation Toolkit

This toolkit evaluates performance-optimization recommendations from multiple sources
(Gemini, GPT-4, Claude, Human expert) against the same diagnostic artifact bundle.
It computes metrics and outputs CSV files.

No example or synthetic results are included. Provide real inputs and scores.

---

## 1) Folder Structure

```
llm_eval_toolkit/
  run_analysis.py
  requirements.txt
  src/
    categories.py
    io_utils.py
    metrics.py
    plots.py
    scoring.py
  inputs/
    gemini.json
    gpt4.json
    claude.json
    human.json
  outputs/
    summary_metrics.csv
    per_recommendation_scored.csv
    similarity_matrix.csv
    validation_report.txt
    scoring_template.csv
```

---

## 2) Recommendation Input Format

Each source file can be **JSON** or **text**:

### JSON format (preferred)

```json
[
  {
    "recommendation_id": "G1",
    "raw_text": "Add a GIN index on products.name for ILIKE search.",
    "category": "indexing",
    "artifact_refs": ["EXPLAIN:q1", "code:search"]
  }
]
```

JSON can also be:

```json
{ "recommendations": [ ... ] }
```

If `recommendation_id` is missing, the tool auto-generates `source_001`, `source_002`, ...

### Text format

One recommendation per line. IDs are auto-generated.

---

## 3) Category Normalization

The toolkit normalizes raw categories into:

- `indexing`
- `query_rewrite`
- `n_plus_one_elimination`
- `caching`
- `transaction_or_batching`
- `invalid_unsafe`
- `other`

Aliases like `redis`, `n+1`, `fts`, `transaction` are mapped automatically.
If no category is provided, a light keyword-based inference is applied.

---

## 4) Manual Scoring CSV (Required for Acceptance Metrics)

Create a CSV with these columns:

| column | description |
| --- | --- |
| source | `gemini`, `gpt4`, `claude`, `human` |
| recommendation_id | must match IDs in input files |
| category_scored | corrected category (can override raw) |
| accepted | 1 or 0 |
| invalid_or_unsafe | 1 or 0 |
| actionability_score | 1–5 |
| correctness_score | 1–5 |
| time_to_analysis_minutes | optional numeric |

Generate a scoring template:

```bash
python3 run_analysis.py --inputs inputs --emit-scoring-template --outputs outputs
```

---

## 5) Run the Toolkit

```bash
cd llm_eval_toolkit
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

python3 run_analysis.py \
  --inputs inputs \
  --scoring scored.csv \
  --outputs outputs \
  --human-source human
```

---

## 6) Outputs

- `summary_metrics.csv`  
  Per-source totals, acceptance/invalid rates, category coverage, Jaccard vs human,
  precision/recall vs human categories, and mean time-to-analysis (if provided).

- `per_recommendation_scored.csv`  
  Input recommendations merged with manual scores.

- `similarity_matrix.csv`  
  Pairwise Jaccard similarity across sources (category sets, `invalid_unsafe` excluded).


