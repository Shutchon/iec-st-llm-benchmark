#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stat_analysis.py — วิเคราะห์ผลตาม PROTOCOL.md §3
อ่าน: JSONL จาก plc_llm_benchmark_lab.py (pilot หรือฉบับเต็ม)
คำนวณ: pass@k (unbiased), Friedman, Wilcoxon+Bonferroni, Cliff's delta, Two-way ANOVA
ผลลัพธ์: พิมพ์ตาราง + เขียน stats_summary.json
ใช้: python3 stat_analysis.py [results.jsonl]
"""
import json
import math
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats


# ── pass@k unbiased estimator (Chen et al. 2021) ─────────────────────────────
def pass_at_k(n, c, k):
    """n = จำนวน runs, c = จำนวน pass, k = ขนาด sample"""
    if n < k or n - c < k:
        return 1.0 if c >= k else 0.0
    return 1.0 - math.prod((n - c - i) / (n - i) for i in range(k))


def cliffs_delta(x, y):
    """Cliff's delta: >0 แปลว่า x เทียบ y ... -1..1 (0 = ทับกัน)"""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    gt = sum((xi > y).sum() for xi in x)
    lt = sum((xi < y).sum() for xi in x)
    return (gt - lt) / (len(x) * len(y))


def main(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    df = pd.DataFrame(rows)
    df["compilation_pass"] = df.get("compilation_pass", False).astype(bool)
    df["functional_pass"] = df.get("functional_pass", False).fillna(False).astype(bool)
    df["truncated"] = df.get("eval_count", pd.Series(dtype=float)).fillna(0) >= 2395
    out = {"source": path, "n_trials": len(df)}

    # ── 1) สรุปรายโมเดล×กลยุทธ์ ──
    print(f"{'model':<24}{'strategy':<11}{'n':>4}{'comp%':>7}{'func%':>7}{'p@1':>6}{'p@5':>6}{'lat':>6}{'trunc%':>7}")
    summ = []
    for (m, s), g in df.groupby(["model", "strategy"]):
        comp = g["compilation_pass"].mean() * 100
        func = g["functional_pass"].mean() * 100
        p1 = g["functional_pass"].mean()
        # pass@5 ต่อโจทย์ (ต้องมี 5 runs ครบจึงคำนวณจริง — ระหว่าง pilot ใช้ runs ที่มี)
        n_runs = g["run_number"].max()
        c_pass = g["functional_pass"].sum()
        p5 = pass_at_k(max(n_runs, 1), int(c_pass), min(5, max(n_runs, 1)))
        lat = g["latency_s"].mean() if "latency_s" in g else float("nan")
        tr = g["truncated"].mean() * 100
        print(f"{m:<24}{s:<11}{len(g):>4}{comp:>6.0f}%{func:>6.0f}%{p1:>6.2f}{p5:>6.2f}{lat:>6.1f}{tr:>6.0f}%")
        summ.append({"model": m, "strategy": s, "n": len(g), "compile_pct": round(comp, 1),
                     "func_pct": round(func, 1), "pass1": round(p1, 4), "passK": round(p5, 4),
                     "latency_mean_s": round(float(lat), 2) if lat == lat else None,
                     "truncated_pct": round(tr, 1)})
    out["per_model_strategy"] = summ

    # ── 2) Friedman ต่อกลยุทธ์ (บล็อก = โจทย์) บน functional pass@1 ──
    friedman = {}
    for s, g in df.groupby("strategy"):
        piv = g.pivot_table(index="task_id", columns="model", values="functional_pass", aggfunc="mean")
        piv = piv.dropna()
        models = list(piv.columns)
        if len(models) >= 3 and len(piv) >= 5:
            stat, p = stats.friedmanchisquare(*[piv[m].values for m in models])
            friedman[s] = {"models": models, "blocks": len(piv),
                           "chi2": round(float(stat), 3), "p": float(p)}
            print(f"\nFriedman [{s}]: χ²={stat:.3f}, p={p:.4g} (n_blocks={len(piv)}, models={len(models)})")
        else:
            friedman[s] = {"note": f"ข้อมูลไม่พอ (models={len(models)}, blocks={len(piv)})"}
    out["friedman"] = friedman

    # ── 3) Wilcoxon + Bonferroni + Cliff's delta (คู่โมเดล, รวมกลยุทธ์) ──
    piv_all = df.pivot_table(index=["strategy", "task_id"], columns="model",
                             values="functional_pass", aggfunc="mean").dropna()
    models = list(piv_all.columns)
    pairs = []
    if len(models) >= 2 and len(piv_all) >= 6:
        alpha = 0.05 / (len(models) * (len(models) - 1) / 2)
        for i in range(len(models)):
            for j in range(i + 1, len(models)):
                a, b = piv_all[models[i]].values, piv_all[models[j]].values
                if np.all(a == b):
                    stat, p = float("nan"), 1.0
                else:
                    stat, p = stats.wilcoxon(a, b, zero_method="wilcox") if (a != b).any() else (float("nan"), 1.0)
                d = cliffs_delta(a, b)
                pairs.append({"a": models[i], "b": models[j], "W": round(float(stat), 1) if stat == stat else None,
                              "p": float(p), "cliffs_delta": round(float(d), 3),
                              "sig_bonferroni": bool(p < alpha)})
        print(f"\nWilcoxon คู่ (α_bonferroni={alpha:.5f}):")
        for pr in sorted(pairs, key=lambda x: x["p"])[:8]:
            print(f"  {pr['a']} vs {pr['b']}: p={pr['p']:.4g} δ={pr['cliffs_delta']:+.2f} "
                  f"{'★' if pr['sig_bonferroni'] else ''}")
    out["wilcoxon_pairs"] = pairs
    out["alpha_bonferroni"] = 0.05 / (len(models) * (len(models) - 1) / 2) if len(models) >= 2 else None

    # ── 4) Two-way ANOVA (statsmodels) ──
    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
        sub = df.dropna(subset=["functional_pass"]).copy()
        sub["model"] = sub["model"].astype(str)
        sub["strategy"] = sub["strategy"].astype(str)
        if sub["model"].nunique() >= 2 and sub["strategy"].nunique() >= 2:
            m = smf.ols("functional_pass ~ C(model) * C(strategy)", data=sub).fit()
            tbl = sm.stats.anova_lm(m, typ=2)
            an = {str(k): {"F": round(float(v["F"]), 2) if v["F"] == v["F"] else None,
                           "p": float(v["PR(>F)"])}
                  for k, v in tbl.iterrows() if k != "Residual"}
            out["anova_two_way"] = an
            print("\nTwo-way ANOVA (functional ~ model × strategy):")
            for k, v in an.items():
                print(f"  {k}: F={v['F']}, p={v['p']:.4g}")
    except Exception as e:
        out["anova_two_way"] = {"error": str(e)[:200]}

    with open("stats_summary.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n→ เขียน stats_summary.json เรียบร้อย (n_trials={len(df)})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "benchmark_results.jsonl")
