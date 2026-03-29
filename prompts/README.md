# Prompt templates (replication package)

This folder contains the **exact prompt templates** used in the Gemini-assisted analyses. Each file is included verbatim with placeholders to be filled by the diagnostic bundle artifacts. These prompts are referenced in the paper’s Replication Package section.

## Files and usage

- `llm_comparison_task.md`  
  **Purpose:** Primary structured prompt used for the Gemini vs human comparison (JSON output schema).  
  **Inputs:** Code fragments, EXPLAIN plans, `pg_stat_statements`, slow-query logs, Locust summary.

- `perf_engineer_prompt.md`  
  **Purpose:** General performance engineer role definition and output format for narrative analyses.

- `prompt_bottleneck_analysis.txt`  
  **Purpose:** N+1 / query-pattern diagnosis from code snippets.  
  **Placeholders:** `[PASTE CODE WITH MULTIPLE QUERIES]`.

- `prompt_query_optimization.txt`  
  **Purpose:** SQL optimization for a slow query.  
  **Placeholders:** `[PASTE SLOW QUERY HERE]`, optional context (table sizes, performance, access pattern).

- `prompt_caching_strategy.txt`  
  **Purpose:** Redis cache design for recommendations endpoint.  
  **Inputs:** Endpoint description, observed latency, call rate, freshness constraints.

## Placeholder conventions

The prompts include bracketed placeholders (e.g., `[PASTE CODE WITH MULTIPLE QUERIES]`). These are filled directly with the frozen diagnostic bundle artifacts (code fragments, EXPLAIN output, `pg_stat_statements`, workload summaries) during each run.

## Replication note

To replicate results, use the **same diagnostic bundle** and fill these templates with the corresponding artifacts. The prompts are intentionally stable; only the **artifact content** changes across runs.
