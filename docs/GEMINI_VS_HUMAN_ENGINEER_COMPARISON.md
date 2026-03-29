# Gemini vs. independent human performance engineer — quantitative comparison 
**Recommended comparison design**

Use a **single frozen diagnostic bundle** (identical artifacts for both raters), **one independent senior human performance engineer** who produces recommendations **before** any exposure to Gemini outputs, and a **blinded post hoc mapping** of items into a **small fixed taxonomy** of categories. Report **counts and percentages** derived from set operations on deduplicated recommendation identities, plus **invalid-flag rates** for Gemini only (human baseline items are constrained to be engineer-approved by protocol). This design is **small** (one session per rater, one bundle, one testbed snapshot), **reviewer-grade** (independence, pre-specified metrics, conservative wording), and **does not require** rebuilding the system—only freezing inputs and collecting two structured lists.


---

## 1) Methodology

### 1.1 Scope and freeze

- **Testbed snapshot:** One commit hash or dated archive of the Node.js + Express application, PostgreSQL schema, Redis usage, and Nginx fronting configuration as exercised in the paper’s load scenario.
- **Diagnostic bundle D (identical for Gemini and human):**  
  - Representative **code fragments** for hot paths (e.g., search, dashboard, recommendations, checkout).  
  - **`EXPLAIN (ANALYZE, BUFFERS)`** (or equivalent) for a fixed set of *K* queries agreed in advance (e.g., *K* = 3–5).  
  - **`pg_stat_statements`** top-*N* summary (fixed *N*, e.g., 15–20) from the same measurement window.  
  - **Slow-query log** excerpt from the **same wall-clock window** as a reference Locust run.  
  - **Workload summary** from Locust (RPS, p50/p95/p99, error rate) for one documented steady-state run (e.g., fixed user count and duration).

No other hints (e.g., prior Gemini drafts, issue trackers) are provided to the human.

### 1.2 Gemini arm (offline advisory)

- Run **one** Gemini configuration documented in the paper (model ID, temperature, max tokens, no browsing unless enabled for all comparisons).
- Prompt instructs: recommendations **only** from the bundle; output as **structured list** (stable IDs `G1`, `G2`, …) with **short title**, **primary category** (from §4), **target** (route/table/query id), and **one-sentence rationale** tied to a named artifact (e.g., `EXPLAIN:q2`, `code:checkout`).
- **Invalid** items are those flagged by the **adjudication pass** (§3.4), not by the model’s self-assessment.

### 1.3 Human arm (independent expert baseline)

- **Eligibility:** Senior performance engineer (e.g., ≥*Y* years relevant experience); **no authorship** on the paper’s implementation and **no prior access** to Gemini outputs for this bundle.
- **Procedure:** The expert receives **only** bundle D and produces a structured list with stable IDs `H1`, `H2`, …, same fields as Gemini (title, category, target, rationale + artifact pointer).
- **Independence:** Expert completes the task **before** receiving Gemini’s list. Access to Gemini output is **only** for adjudication after both lists exist (or a third neutral adjudicator maps overlap without changing the raw lists).

### 1.4 Adjudication and deduplication

- **Canonical identity** for matching: a tuple **(primary category, target signature)** where `target signature` is a normalized string (e.g., lowercased route template + primary table names, or query id). Ambiguous items are resolved by a **pre-defined rule** (e.g., prefer table list sorted lexicographically).
- **Duplicate collapse:** Within each list, duplicates mapping to the same canonical identity count as **one** recommendation before overlap statistics.
- **Mapping session:** Two authors (or one author + adjudicator) label pairs: **exact match**, **partial match** (same family, different object), **unrelated**. Only **exact** counts toward **overlap count** in the primary table; **partial** may be reported as sensitivity analysis in supplementary material if space allows.

### 1.5 What to pre-register (even informally for revision)

- Bundle checksum or version id `D_v1`.  
- *K* queries explained, *N* for pg_stat_statements, Locust run id.  
- Category taxonomy (§4).  
- Definitions of exact vs. partial match.  
- Primary vs. secondary endpoints (overlap count + agreement rate primary; partial optional).

---

## 2) Comparison metrics (exact definitions)

Let **G** = deduplicated set of Gemini canonical identities, **H** = deduplicated set of human canonical identities. Let **G_valid** ⊆ **G** be Gemini items **not** flagged invalid after adjudication (§3.4).

| Metric | Definition | Formula / rule |
|--------|------------|----------------|
| **Overlap count** | Number of canonical identities appearing in **both** lists under **exact** match | \(\|G \cap H\|\) after adjudication |
| **Agreement rate** | Proportion of human recommendations also found in Gemini (human-centric recall of Gemini coverage) | \(\|G \cap H\| / \|H\|\) if \(\|H\|>0\); report **ND** if \(H=\emptyset\) |
| **Gemini precision-like coverage** (optional label) | Proportion of Gemini recommendations that match a human item | \(\|G \cap H\| / \|G\|\) if \(\|G\|>0\) |
| **Gemini-only (valid)** | Gemini items with no exact human match, **and** not invalid | \(G_{\text{valid}} \setminus H\) |
| **Human-only** | Human items with no exact Gemini match | \(H \setminus G\) |
| **Invalid Gemini suggestions** | Count (and rate) of Gemini items failing rubric in §3.4 | `n_invalid_G`, `n_invalid_G / \|G\|` |

**Conservative reporting:** State explicitly that **agreement rate** is **not** inter-rater reliability in the psychometric sense; it is **overlap relative to the independent human list** under a **transparent identity rule**. Do not equate overlap with “correctness” unless a separate validation study exists.

**Invalid rate (Gemini-only):** Human list is produced under expert judgment; invalid counts are reported **for Gemini** to address unsafe or hallucinated DDL/SQL, wrong objects, or contradictions to the bundle.

---

## 3) Recommendation coding rubric

### 3.1 Primary categories (mutually exclusive)

Assign **exactly one** primary category per recommendation:

| Code | Category | Inclusion examples | Exclude / borderline |
|------|-----------|----------------------|----------------------|
| **IDX** | Indexing / physical design | New or altered indexes; BRIN/GIN/trigram; selective partial indexes | Vague “add indexes” without object |
| **QRW** | Query rewrite / plan shape | Rewriting joins, removing SELECT *, replacing correlated subqueries | Pure ORM config with no SQL shape |
| **N1** | N+1 / chatty access elimination | Batching, `IN` lists, JOIN consolidation, DataLoader-style patterns | Generic “reduce queries” without mechanism |
| **CCH** | Caching | Redis TTL, cache-aside, key design, invalidation | CDN-only if not in bundle scope |
| **TXN** | Transactions / consistency | Explicit transactions, idempotency, ordering of writes | Unrelated locking theory |
| **POOL** | Pooling / saturation / concurrency | Pool sizing vs. DB `max_connections`, thread limits | OS tuning not tied to bundle |
| **OBS** | Measurement / diagnosis | What to trace next, which metric to watch | No concrete next step |
| **INV** | Invalid / unsafe / hallucinated | Wrong dialect, nonexistent tables/columns, destructive ops without staging | Borderline → mark **INV** if violates bundle schema |

**Canonical overlap buckets (pre-registered):** For the Gemini–human overlap table, map categories to a small fixed set before matching:

- **query_optimization**: `query_rewrite`, `n+1`, `join_optimization`, `indexing`, `fts`, `trigram`, `payload_reduction`, `response_size`  
- **caching**: `caching`, `redis`  
- **batching_txn**: `batching`, `transaction_handling`  

### 3.2 Target signature (for matching)

Normalize to a single string, e.g.  
`route:<method_path_lower> | tables:<sorted_csv> | query:<id_if_any>`  
Omit empty components. Two items **match exactly** only if **category code** and **target signature** match after normalization.

### 3.3 Partial match (optional sensitivity)

Same **category** and overlapping **tables** but different mechanism (e.g., human proposes composite index, Gemini proposes covering index on different columns): label **partial**. Do **not** enter primary overlap table unless promoted by a written rule (e.g., “same tables + same category”).

### 3.4 Invalid Gemini item (adjudicator checklist)

Flag **invalid** if **any** applies:

1. References object **not present** in bundle schema or code.  
2. SQL not valid for **PostgreSQL 15** as stated in the paper.  
3. Recommends **production-unsafe** change without staging/migration path (e.g., `DROP INDEX` on live hot path with no alternative).  
4. **Contradicts** stated bundle evidence (e.g., recommends sequential scan “fix” when EXPLAIN already index-only).  
5. **Generic** boilerplate with **no** tie to an artifact id (after one remediation pass—optional).

---

## 4) Implementation in this repository

After adjudication, place the **Gemini** list in `llm_comparison_lite/data/gemini.json` and the **independent human** list in `llm_comparison_lite/data/human.json` (same schema as `LIGHTWEIGHT_COMPARISON.md`: `endpoint`, `raw_text`, `category`, `accepted_by_human`, `invalid_or_hallucinated`, `safety_risk`). Set `invalid_or_hallucinated` only on Gemini rows that fail the invalid checklist (§3.4).

Then run:

```bash
cd llm_comparison_lite
python3 -m pip install -r requirements.txt
python3 run_paper_overlap.py --data-dir data --out-dir outputs
```

This writes **`outputs/paper_overlap_summary.csv`** (numeric row for the table). **Canonical identity** matches the lite pipeline: `endpoint` (lowercased) + **normalized** `category` (see `llm_comparison_lite/categories.py`). If the paper uses a richer target signature (tables/query id), extend `paper_overlap.canonical_key()` in one place and document the change in Methods.

The broader three-model comparison remains **`run_analysis.py`** (Jaccard across Gemini/GPT-4/Claude). Use **`run_paper_overlap.py`** specifically for the **reviewer’s Gemini vs human** table.

---

## 5) Conservative claims checklist

- Say **“overlap”** and **“agreement under definition X”**, not **“Gemini matches human accuracy.”**  
- Report **invalid rate for Gemini**; avoid implying the human made zero errors unless independently audited.  
- One **expert** = pilot evidence; phrase as **“illustrative quantitative comparison”** if *n* = 1.  
- If adding a **second** expert later, report **inter-human overlap** separately.

---

*End of document.*
