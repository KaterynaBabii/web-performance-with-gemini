#!/usr/bin/env python3
"""
Export paper-ready tables from results/baseline, results/gemini, and ablation folders.

Outputs:
  - results/paper_export/PAPER_TABLE_GRID.md  — Table 3 (50–300 users) + § Ablation study (300 users) + LaTeX snippet
  - results/paper_export/PAPER_TABLE_GRID.tex
  - results/paper_export/PAPER_TABLE_ABLATION_300.md  — Table 4 copy

Welch / Mann–Whitney: SciPy recommended (`pip install -r requirements.txt`).

Usage:
  python3 scripts/export-paper-tables.py
"""

from __future__ import annotations

import importlib.util
import math
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CS_PATH = Path(__file__).resolve().parent / "compute-statistics.py"
_spec = importlib.util.spec_from_file_location("computestats", _CS_PATH)
_cs = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_cs)

load_json = _cs.load_json
load_csv = _cs.load_csv
compute_stats = _cs.compute_stats
t_confidence_interval = _cs.t_confidence_interval
mann_whitney_u_two_sided = _cs.mann_whitney_u_two_sided
welch_t_pvalue_two_sided = _cs.welch_t_pvalue_two_sided

GRID_LOADS = ["50", "100", "150", "200", "250", "300"]
EXPECTED_REPS = 10

# Ablation study @ 300 users (Table 4): (display name, results folder, load).
# Baseline / Full Gemini **must** use existing main-grid files only (no duplicate runs).
CONFIGS: list[tuple[str, str, int]] = [
    ("Baseline", "baseline", 300),
    ("Index only", "index_only", 300),
    ("Query opt", "query_opt", 300),
    ("Cache only", "cache_only", 300),
    ("Full Gemini", "gemini", 300),
]
LOAD_ABLATION = str(CONFIGS[0][2])  # "300"

METRIC_NAMES = [
    "Avg latency (ms)",
    "P95 latency (ms)",
    "Throughput (req/s)",
    "Cache hit (%)",
]
# JSON / export field names (Table 3 metrics align with run JSON after canon-metrics-json.py)
METRIC_KEYS = ["avg_latency_ms", "p95_latency_ms", "throughput_rps", "cache_hit_pct"]


def count_runs(project_root: Path, folder: str, load: str) -> int:
    base = project_root / "results" / folder
    return len(list(base.glob(f"{load}_run*.json")))


def grid_readiness_issues(project_root: Path) -> list[str]:
    issues: list[str] = []
    for load in GRID_LOADS:
        nb = count_runs(project_root, "baseline", load)
        ng = count_runs(project_root, "gemini", load)
        if nb == 0 and ng == 0:
            issues.append(f"Load **{load}**: no `*_run*.json` files (missing load level).")
            continue
        if nb < EXPECTED_REPS:
            issues.append(
                f"Load **{load}** baseline: **n = {nb}** (expected **{EXPECTED_REPS}**)."
            )
        if ng < EXPECTED_REPS:
            issues.append(
                f"Load **{load}** gemini: **n = {ng}** (expected **{EXPECTED_REPS}**)."
            )
    return issues


def ablation_readiness_issues(project_root: Path) -> list[str]:
    issues: list[str] = []
    for _label, folder, _load in CONFIGS:
        n = count_runs(project_root, folder, LOAD_ABLATION)
        if n == 0:
            issues.append(
                f"Table 4 **{_label}** (`results/{folder}/`): no `{LOAD_ABLATION}_run*.json`."
            )
        elif n < EXPECTED_REPS:
            issues.append(
                f"Table 4 **{_label}** (`results/{folder}/`): **n = {n}** (expected **{EXPECTED_REPS}**)."
            )
    return issues


def run_suffix(path: Path) -> str | None:
    m = re.search(r"_run(\d+)\.json$", path.name)
    return m.group(1) if m else None


def _float_field(data: dict, *keys: str) -> float | None:
    for k in keys:
        if k not in data or data[k] is None:
            continue
        try:
            return float(data[k])
        except (TypeError, ValueError):
            continue
    return None


def collect_series(
    project_root: Path, folder: str, load: str
) -> tuple[list[float], list[float], list[float], list[float], int]:
    """Returns (avg_ms, p95_ms, cache_pct, throughput_rps, n_runs)."""
    base = project_root / "results" / folder
    json_files = sorted(base.glob(f"{load}_run*.json"))
    avg_ms: list[float] = []
    p95_ms: list[float] = []
    cache_pct: list[float] = []
    thr: list[float] = []

    for jf in json_files:
        suf = run_suffix(jf)
        if suf is None:
            continue
        data = load_json(str(jf))
        if not data:
            continue
        a = _float_field(
            data, "avg_latency_ms", "avg_ms"
        )
        p = _float_field(
            data, "p95_latency_ms", "p95_ms"
        )
        c = _float_field(
            data, "cache_hit_pct", "cache_hit_ratio"
        )
        tput = _float_field(data, "throughput_rps", "throughput")
        if tput is None or (not math.isnan(float(tput)) and float(tput) <= 0):
            lc = base / f"locust_{load}_run{suf}.csv"
            if not lc.exists():
                lc = base / f"{load}_run{suf}_stats.csv"
            row = load_csv(str(lc)) if lc.exists() else None
            if row and row.get("Requests/s"):
                tput = float(row["Requests/s"])
            else:
                tput = float("nan")

        avg_ms.append(float(a if a is not None else 0))
        p95_ms.append(float(p if p is not None else 0))
        cache_pct.append(float(c if c is not None else 0))
        thr.append(float(tput))

    n = len(avg_ms)
    return avg_ms, p95_ms, cache_pct, thr, n


def row_stats(vals: list[float]) -> tuple[float, float, int, float, float]:
    finite = [
        float(v)
        for v in vals
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    ]
    mean, std, n = compute_stats(finite)
    lo, hi = t_confidence_interval(mean, std, n)
    return mean, std, n, lo, hi


def fmt_pm(mean: float, std: float, d: int = 2) -> str:
    if math.isnan(mean):
        return "---"
    if math.isnan(std) or std == 0:
        return f"{mean:.{d}f}"
    return f"{mean:.{d}f} $\\pm$ {std:.{d}f}"


def fmt_ci(lo: float, hi: float, d: int = 2) -> str:
    if math.isnan(lo) or math.isnan(hi):
        return "---"
    return f"[{lo:.{d}f},\\,{hi:.{d}f}]"


def cv_ratio(mean: float, std: float) -> float:
    if math.isnan(mean):
        return float("nan")
    if abs(mean) < 1e-9:
        return float("inf") if (not math.isnan(std) and std > 0) else 0.0
    return abs(std / mean)


def series_close(
    a: tuple[list[float], list[float], list[float], list[float], int],
    b: tuple[list[float], list[float], list[float], list[float], int],
    tol: float = 1e-5,
) -> bool:
    if a[4] != b[4]:
        return False
    for i in range(4):
        for x, y in zip(a[i], b[i]):
            if math.isnan(x) and math.isnan(y):
                continue
            if math.isnan(x) or math.isnan(y):
                return False
            if abs(x - y) > tol:
                return False
    return True


def main() -> None:
    project_root = _ROOT
    export_dir = project_root / "results" / "paper_export"
    export_dir.mkdir(parents=True, exist_ok=True)
    out_md = export_dir / "PAPER_TABLE_GRID.md"
    out_tex = export_dir / "PAPER_TABLE_GRID.tex"
    out_abl = export_dir / "PAPER_TABLE_ABLATION_300.md"

    readiness = grid_readiness_issues(project_root)
    abl_readiness = ablation_readiness_issues(project_root)

    status_block = ""
    if readiness:
        status_block = (
            "## STATUS: NOT PUBLICATION-READY (main grid)\n\n"
            "**Do not paste this export into the camera-ready paper as final results.**\n\n"
            + "\n".join(f"- {line}" for line in readiness)
            + "\n\nComplete **`./scripts/run-benchmark-grid.sh`**, then re-run this exporter. "
            "See **`PAPER_AND_BENCHMARK.md`**.\n\n---\n\n"
        )

    if abl_readiness:
        status_block += (
            "## STATUS: NOT PUBLICATION-READY (Table 4 ablation @ 300 users)\n\n"
            + "\n".join(f"- {line}" for line in abl_readiness)
            + "\n\nRun **`./scripts/run-ablation-300-paper.sh`** (and the main grid for baseline/gemini). "
            "See **`PAPER_AND_BENCHMARK.md`**.\n\n---\n\n"
        )

    # Cache all main-grid series once (Table 3 + Table 4 baseline/gemini reuse)
    series_cache: dict[tuple[str, str], tuple[list[float], list[float], list[float], list[float], int]] = {}
    for load in GRID_LOADS:
        series_cache[("baseline", load)] = collect_series(project_root, "baseline", load)
        series_cache[("gemini", load)] = collect_series(project_root, "gemini", load)

    lines_md: list[str] = [
        "# Paper tables (generated by `scripts/export-paper-tables.py`)",
        "",
        status_block,
        "Per-run JSON: `results/{config}/{load}_run{k}.json` (+ `locust_{load}_run{k}.csv` for throughput).",
        "",
        "> **Main grid:** 6 loads (50, 100, 150, 200, 250, 300) × **10** reps × (baseline + gemini).",
        "",
        "> **Welch $p$:** SciPy when installed; else normal approximation (see script header).",
        "",
        "## Table 3. Main benchmark (all metrics per load)",
        "",
        "For each load level, four metrics from run JSON (see `scripts/canon-metrics-json.py`): "
        "**`avg_latency_ms`**, **`p95_latency_ms`**, **`throughput_rps`**, **`cache_hit_pct`** — each with "
        "mean ± SD, 95% CI, Welch $p$ and Mann–Whitney $p$ (Baseline vs Gemini).",
        "",
    ]

    tex_rows: list[str] = []

    for load in GRID_LOADS:
        b_key = ("baseline", load)
        g_key = ("gemini", load)
        b_avg, b_p95, b_cache, b_thr, nb = series_cache[b_key]
        g_avg, g_p95, g_cache, g_thr, ng = series_cache[g_key]

        if nb == 0 and ng == 0:
            lines_md.append(f"### Load {load} users\n\n*No data files found.*\n")
            tex_rows.append(f"% load {load}: no data\n")
            continue

        lines_md.append(f"### Load {load} users\n")
        lines_md.append(f"- **Baseline** runs: **n = {nb}** | **Gemini** runs: **n = {ng}**\n")

        for name, key, b_vals, g_vals in [
            (METRIC_NAMES[0], METRIC_KEYS[0], b_avg, g_avg),
            (METRIC_NAMES[1], METRIC_KEYS[1], b_p95, g_p95),
            (METRIC_NAMES[2], METRIC_KEYS[2], b_thr, g_thr),
            (METRIC_NAMES[3], METRIC_KEYS[3], b_cache, g_cache),
        ]:
            if not b_vals or not g_vals:
                lines_md.append(f"#### {name} (`{key}`)\n\nInsufficient paired series.\n")
                continue
            mb, sb, nb_, lob, hib = row_stats(b_vals)
            mg, sg, ng_, log, hig = row_stats(g_vals)
            _, p_mw = mann_whitney_u_two_sided(b_vals, g_vals)
            p_welch, t_w, df_w = welch_t_pvalue_two_sided(b_vals, g_vals)

            lines_md.append(f"#### {name} (`{key}`)\n")
            lines_md.append(
                f"| Config | mean ± SD | 95% CI | Welch $p$ | Mann–Whitney $p$ |\n"
                f"|--------|-----------|--------|------------|------------------|\n"
                f"| Baseline | {fmt_pm(mb, sb)} | {fmt_ci(lob, hib)} | — | — |\n"
                f"| Gemini | {fmt_pm(mg, sg)} | {fmt_ci(log, hig)} | — | — |\n"
            )
            pw = f"{p_welch:.4g}" if not math.isnan(p_welch) else "n/a"
            pm = f"{p_mw:.4g}" if not math.isnan(p_mw) else "n/a"
            lines_md.append(
                f"**Tests (Baseline vs Gemini):** Welch $t={t_w:.3f}$ (df $\\approx$ {df_w:.1f}$\\,$), "
                f"$p_{{\\mathrm{{Welch}}}}$ = {pw}; Mann–Whitney $p$ = {pm}.\n"
            )

            tex_rows.append(
                f"% {name} load {load}\n"
                f"% Baseline {mb:.2f} pm {sb:.2f} CI {fmt_ci(lob, hib)} n={nb_}\n"
                f"% Gemini   {mg:.2f} pm {sg:.2f} CI {fmt_ci(log, hig)} n={ng_}\n"
                f"% p_welch={pw} p_mw={pm}\n"
            )

        lines_md.append("")

    # LaTeX: average latency only (extend in paper as needed)
    lines_md.append("---\n## LaTeX snippet (average latency only — extend as needed)\n")
    tex = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Average latency (ms, mean $\pm$ SD) and two-sided $p$-values (Baseline vs Gemini-informed).}",
        r"\label{tab:grid-avg}",
        r"\begin{tabular}{lcccccc}",
        r"\hline",
        r"Users & Baseline & Gemini & $p_{\mathrm{Welch}}$ & $p_{\mathrm{MW}}$ & $n_b$ & $n_g$ \\",
        r"\hline",
    ]
    for load in GRID_LOADS:
        b_avg, _, _, _, nb = series_cache[("baseline", load)]
        g_avg, _, _, _, ng = series_cache[("gemini", load)]
        if not b_avg or not g_avg:
            tex.append(f"{load} & --- & --- & --- & --- & {nb} & {ng} \\\\")
            continue
        mb, sb, nb_, _, _ = row_stats(b_avg)
        mg, sg, ng_, _, _ = row_stats(g_avg)
        p_welch, _, _ = welch_t_pvalue_two_sided(b_avg, g_avg)
        _, p_mw = mann_whitney_u_two_sided(b_avg, g_avg)
        pw = f"{p_welch:.3g}" if not math.isnan(p_welch) else "n/a"
        pm = f"{p_mw:.3g}" if not math.isnan(p_mw) else "n/a"
        tex.append(
            f"{load} & ${mb:.1f} \\pm {sb:.1f}$ & ${mg:.1f} \\pm {sg:.1f}$ & {pw} & {pm} & {nb_} & {ng_} \\\\"
        )
    tex.extend([r"\hline", r"\end{tabular}", r"\end{table*}"])
    tex_str = "\n".join(tex)
    out_tex.write_text(tex_str, encoding="utf-8")
    lines_md.append("```latex\n" + tex_str + "\n```\n")

    # --- Ablation study (300 users) — Table 4 in the paper ---
    lines_md.append("\n---\n")
    lines_md.append("## Ablation study (300 users)\n")
    lines_md.append("")
    lines_md.append(
        "*This section is **Table 4** in the manuscript.* Mean ± SD and 95% CI (Student’s $t$) for "
        "**`avg_latency_ms`**, **`p95_latency_ms`**, **`throughput_rps`**; "
        "**Baseline** and **Full Gemini** reuse `results/baseline/300_run*.json` and "
        "`results/gemini/300_run*.json` (same runs as Table 3 @300 users)."
    )
    lines_md.append("")

    ablation_series: dict[str, tuple[list[float], list[float], list[float], list[float], int]] = {}
    for _label, folder, load_u in CONFIGS:
        assert str(load_u) == LOAD_ABLATION, "CONFIGS load must match LOAD_ABLATION"
        if folder == "baseline":
            ablation_series[folder] = series_cache[("baseline", LOAD_ABLATION)]
        elif folder == "gemini":
            ablation_series[folder] = series_cache[("gemini", LOAD_ABLATION)]
        else:
            ablation_series[folder] = collect_series(project_root, folder, LOAD_ABLATION)

    lines_abl: list[str] = [
        "# Table 4 — Ablation @ 300 users (generated)",
        "",
        "| Config | Avg Lat (ms) | P95 (ms) | Throughput (req/s) | n |",
        "|--------|-------------|----------|---------------------|---|",
    ]

    cv_warnings: list[str] = []
    sanity_errors: list[str] = []
    ablation_missing_labels: list[str] = []

    for label, folder, _load_u in CONFIGS:
        s = ablation_series[folder]
        av, p9, _ca, th, n_files = s
        if n_files == 0:
            line = f"| {label} | — | — | — | 0 |"
            lines_abl.append(line)
            lines_md.append(line)
            ablation_missing_labels.append(label)
            continue

        ma, sa, _na, loa, hia = row_stats(av)
        mp, sp, _np, lop, hip = row_stats(p9)
        mt, st, _nt, lot, hit = row_stats(th)

        lines_abl.append(
            f"| {label} | {fmt_pm(ma, sa)} | {fmt_pm(mp, sp)} | {fmt_pm(mt, st)} | {n_files} |"
        )
        lines_md.append(
            f"| {label} | {fmt_pm(ma, sa)} | {fmt_pm(mp, sp)} | {fmt_pm(mt, st)} | {n_files} |"
        )

        if n_files != EXPECTED_REPS:
            sanity_errors.append(
                f"Sanity check 4 FAILED: **{label}** — expected n={EXPECTED_REPS}, found n={n_files}."
            )

        for metric_name, m, stdev in [
            ("avg_latency_ms", ma, sa),
            ("p95_latency_ms", mp, sp),
            ("throughput_rps", mt, st),
        ]:
            cr = cv_ratio(m, stdev)
            if not math.isnan(cr) and cr > 0.40:
                extra_hint = (
                    f"`ABLATION_VARIANT={folder} ABLATION_START_REP=11 ABLATION_REPS=5 ./scripts/run-ablation-300-paper.sh`"
                    if folder in ("index_only", "query_opt", "cache_only")
                    else f"`./scripts/run-benchmark-grid.sh` with `BENCHMARK_GRID_SYSTEMS={folder}` (or full grid)"
                )
                cv_warnings.append(
                    f"**CV warning** ({label} / {metric_name}): SD/|mean| = {cr:.3f} > 0.40. "
                    f"Run **5 additional repetitions** then re-export: {extra_hint}."
                )
                sanity_errors.append(
                    f"Sanity check 5 FAILED: **{label}** `{metric_name}` — SD/|mean|={cr:.3f} > 0.40 "
                    f"(mean={m:.4f}, SD={stdev:.4f})."
                )

    lines_md.append("")
    if cv_warnings:
        lines_md.append("### Coefficient-of-variation (CV) warnings\n")
        for w in cv_warnings:
            lines_md.append(f"- {w}\n")
        lines_md.append("")

    lines_md.append(
        "*Throughput uses Locust **Aggregated** `Requests/s` when present; latencies from `/metrics` JSON.*\n"
    )

    lines_md.append("\n#### 95% confidence intervals (Student’s $t$, same metrics as above)\n")
    lines_abl.append("")
    lines_abl.append("## 95% CI (Student’s t)")
    for label, folder, _load_u in CONFIGS:
        s = ablation_series[folder]
        av, p9, _ca, th, n_files = s
        if n_files == 0:
            lines_md.append(f"- **{label}:** — (no data)\n")
            lines_abl.append(f"- **{label}:** — (no data)")
            continue
        _ma, _sa, _, loa, hia = row_stats(av)
        _mp, _sp, _, lop, hip = row_stats(p9)
        _mt, _st, _, lot, hit = row_stats(th)
        lines_md.append(
            f"- **{label}:** Avg lat {fmt_ci(loa, hia)} ms; P95 {fmt_ci(lop, hip)} ms; "
            f"Throughput {fmt_ci(lot, hit)} req/s\n"
        )
        lines_abl.append(
            f"- **{label}:** Avg lat {fmt_ci(loa, hia)} ms; P95 {fmt_ci(lop, hip)} ms; "
            f"Throughput {fmt_ci(lot, hit)} req/s"
        )

    out_abl.write_text("\n".join(lines_abl) + "\n", encoding="utf-8")

    # --- Sanity: Table 4 Baseline/Gemini must match cached 300-user grid series ---
    b300_cached = series_cache[("baseline", LOAD_ABLATION)]
    g300_cached = series_cache[("gemini", LOAD_ABLATION)]
    if not series_close(ablation_series["baseline"], b300_cached):
        sanity_errors.append(
            "Internal error: Table 4 Baseline series != main-grid baseline @300 "
            f"(baseline n={ablation_series['baseline'][4]} vs cache n={b300_cached[4]})."
        )
    if not series_close(ablation_series["gemini"], g300_cached):
        sanity_errors.append(
            "Internal error: Table 4 Full Gemini series != main-grid gemini @300."
        )

    # Table 3 @300 vs Table 4 (checks 1–3): **expected** = Table 3 / main grid files; **found** = ablation section
    def _check_t3_t4(check_num: int, cfg: str, metric_idx: int, metric_label: str, key: str) -> None:
        t3 = series_cache[(cfg, LOAD_ABLATION)][metric_idx]
        t4 = ablation_series[cfg][metric_idx]
        t3m, t3s, t3n, _, _ = row_stats(t3)
        t4m, t4s, t4n, _, _ = row_stats(t4)
        if abs(t3m - t4m) > 1e-3 or abs(t3s - t4s) > 1e-3 or t3n != t4n:
            role = "Baseline" if cfg == "baseline" else "Full Gemini"
            sanity_errors.append(
                f"Sanity check {check_num} FAILED: {role} @300 **`{key}`** ({metric_label}) — "
                f"Table 4 must match Table 3 (same JSON under `results/{cfg}/300_run*.json`). "
                f"**Expected** (Table 3 / main grid): {fmt_pm(t3m, t3s)} (n={t3n}). "
                f"**Found** (ablation reuse path): {fmt_pm(t4m, t4s)} (n={t4n}). "
                f"If you hand-copied Table 4 into the paper, replace with the **Expected** line."
            )

    if series_cache[("baseline", LOAD_ABLATION)][0] and series_cache[("gemini", LOAD_ABLATION)][0]:
        _check_t3_t4(1, "baseline", 0, METRIC_NAMES[0], METRIC_KEYS[0])
        _check_t3_t4(2, "gemini", 0, METRIC_NAMES[0], METRIC_KEYS[0])
        _check_t3_t4(3, "gemini", 1, METRIC_NAMES[1], METRIC_KEYS[1])

    lines_md.append("\n---\n## Sanity checks (automated)\n")
    lines_md.append(
        "1. Baseline **avg** @300: Table 4 ≡ Table 3 (`avg_latency_ms`). "
        "2. Full Gemini **avg** @300: Table 4 ≡ Table 3. "
        "3. Full Gemini **P95** @300: Table 4 ≡ Table 3 (`p95_latency_ms`). "
        "4. All Table 4 rows **n = 10**. "
        "5. No **CV** (SD/|mean|) > 0.40 on avg / P95 / throughput per config.\n"
    )
    if series_cache[("baseline", LOAD_ABLATION)][0]:
        bm, bs, bn, _, _ = row_stats(series_cache[("baseline", LOAD_ABLATION)][0])
        lines_md.append(
            f"- **Reference @300 (Table 3, Baseline `avg_latency_ms`):** {fmt_pm(bm, bs)} (n={bn}) "
            f"— Table 4 “Baseline” must show this exactly.\n"
        )
    if series_cache[("gemini", LOAD_ABLATION)][0]:
        gm, gs, gn, _, _ = row_stats(series_cache[("gemini", LOAD_ABLATION)][0])
        gpm, gps, gpn, _, _ = row_stats(series_cache[("gemini", LOAD_ABLATION)][1])
        lines_md.append(
            f"- **Reference @300 (Table 3, Gemini `avg_latency_ms`):** {fmt_pm(gm, gs)} (n={gn}); "
            f"**`p95_latency_ms`:** {fmt_pm(gpm, gps)} (n={gpn}) — Table 4 “Full Gemini” must match.\n"
        )
    if ablation_missing_labels:
        lines_md.append(
            "\n**Table 4 incomplete:** no `300_run*.json` yet for: "
            + ", ".join(f"**{x}**" for x in ablation_missing_labels)
            + ". Run `./scripts/run-ablation-300-paper.sh`. "
            "Hard checks 4–5 apply only where data exists.\n"
        )
    if sanity_errors:
        lines_md.append("\n**FAILED (hard):**\n")
        for e in sanity_errors:
            lines_md.append(f"- {e}\n")
        lines_md.append(
            "\nDo not paste mismatched values into the paper (e.g. old Table 4 Baseline **15848 ± 933** "
            "when the grid says **15116 ± 1600**). **Expected** above is always from measured `results/`.\n"
        )
    elif not ablation_missing_labels:
        lines_md.append(
            "\n- Checks **1–3**: Table 4 **Baseline** / **Full Gemini** ≡ Table 3 @300 (same files).\n"
            "- Check **4**: all configs **n = 10**.\n"
            "- Check **5**: **CV** ≤ 0.40 for avg / P95 / throughput.\n"
        )

    out_md.write_text("\n".join(lines_md), encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_tex}")
    print(f"Wrote {out_abl}")
    if cv_warnings:
        print("\n=== CV WARNINGS (see markdown) ===", file=sys.stderr)
        for w in cv_warnings:
            print(w, file=sys.stderr)
    if ablation_missing_labels:
        print(
            "\n=== NOTE: Table 4 missing data for: "
            + ", ".join(ablation_missing_labels)
            + " ===",
            file=sys.stderr,
        )
    if sanity_errors:
        print("\n=== SANITY CHECK FAILED (hard) ===", file=sys.stderr)
        for e in sanity_errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    if not ablation_missing_labels:
        print("\n=== SANITY CHECKS: OK ===")
    else:
        print("\n=== SANITY CHECKS: OK (Table 4 partial — see NOTE) ===")


if __name__ == "__main__":
    main()
