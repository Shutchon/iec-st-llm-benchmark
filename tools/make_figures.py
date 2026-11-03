#!/usr/bin/env python3
"""สร้างกราฟ 2 รูปสำหรับบทควาท (งบ 8 หน้า: มีกราฟแค่ 2 รูป)
Fig1: functional pass@1/@5 ต่อโมเดล (RQ1)
Fig2: trade-off ความแม่น vs ความเร็ว vs ขนาด (RQ3)
บันทึกเป็น PDF (เวกเตอร์สำหรับ LaTeX) + PNG 300dpi"""
import json, os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 8.5, "font.family": "serif",
                     "axes.grid": True, "grid.alpha": 0.3, "grid.linestyle": ":"})

rows = [json.loads(l) for l in open("benchmark_results.jsonl", encoding="utf-8")]
passk = json.load(open("pass_at_k.json"))

# ── ข้อมูลเสริมจาก roster ──
META = {  # tag: (ชื่อสั้น, GB, tier)
    "qwen3-coder:30b": ("Qwen3-Coder-30B", 19, "A"),
    "gpt-oss:20b": ("GPT-OSS-20B", 13, "A"),
    "qwen3.8:27b": ("Qwen3.8-27B", 18, "A"),
    "qwen3.5:27b": ("Qwen3.5-27B", 17, "A"),
    "gemma4:12b": ("Gemma4-12B", 8, "A"),
    "qwen2.5-coder:14b": ("Qwen2.5-Coder-14B", 9, "B"),
    "deepseek-coder-v2:16b": ("DS-Coder-V2-16B", 9, "B"),
    "llama3.1:8b": ("Llama-3.1-8B", 5, "B"),
}
tps = defaultdict(list)
for r in rows:
    if r.get("status") == "ok" and r.get("tokens_per_s"):
        tps[r["model"]].append(r["tokens_per_s"])
tps_mean = {m: sum(v)/len(v) for m, v in tps.items()}

# ── Fig 1: pass@1 / pass@5 ──
models = sorted(passk, key=lambda m: passk[m]["1"])
labels = [META[m][0] for m in models]
p1 = [passk[m]["1"] for m in models]
p5 = [passk[m]["5"] for m in models]
fig, ax = plt.subplots(figsize=(3.45, 2.5))  # 1 คอลัมน์ IEICE ≈ 84mm
y = range(len(models))
ax.barh(y, p1, height=0.62, color="#2a6f97", label="pass@1")
ax.barh(y, [b - a for a, b in zip(p1, p5)], left=p1, height=0.62,
        color="#bcd4e6", label="pass@5")
ax.set_yticks(list(y)); ax.set_yticklabels(labels)
ax.set_xlabel("Functional pass rate (30 tasks)")
ax.set_xlim(0, 0.72)
ax.legend(loc="lower right", fontsize=7.5, framealpha=0.9)
for i, m in enumerate(models):
    ax.text(passk[m]["5"] + 0.012, i, f'{passk[m]["1"]:.2f}', va="center", fontsize=7)
fig.tight_layout()
fig.savefig("paper/fig1_passk.pdf"); fig.savefig("paper/fig1_passk.png", dpi=300)
plt.close(fig)

# ── Fig 2: trade-off แม่น × เร็ว × ขนาด ──
fig, ax = plt.subplots(figsize=(3.45, 2.6))
COLOR = {"A": "#2a6f97", "B": "#c44e52"}
for m in passk:
    name, gb, tier = META[m]
    x = passk[m]["1"]
    yv = tps_mean.get(m, 0)
    ax.scatter(x, yv, s=gb * 14, c=COLOR[tier], alpha=0.85, edgecolors="k", linewidths=0.5, zorder=3)
    dy = {"gpt-oss:20b": 1.15, "qwen2.5-coder:14b": 1.12, "gemma4:12b": 1.12,
          "qwen3-coder:30b": 1.14, "deepseek-coder-v2:16b": 0.86, "llama3.1:8b": 1.14,
          "qwen3.8:27b": 1.13, "qwen3.5:27b": 1.12}[m]
    ax.annotate(name, (x, yv), xytext=(5, 10 * (dy - 1) + 4), textcoords="offset points", fontsize=6.6)
ax.set_yscale("log")
ax.set_xlabel("Functional pass@1")
ax.set_ylabel("Throughput (tokens/s, log)")
ax.set_xlim(-0.03, 0.60)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], marker="o", ls="", color=COLOR["A"], label="Tier A (2025–26)"),
                   Line2D([], [], marker="o", ls="", color=COLOR["B"], label="Tier B (2024)")],
          loc="upper left", fontsize=7, framealpha=0.9)
ax.text(0.97, 0.03, "bubble size = model size (GB)", transform=ax.transAxes,
        ha="right", fontsize=6.5, style="italic", color="#555")
fig.tight_layout()
fig.savefig("paper/fig2_tradeoff.pdf"); fig.savefig("paper/fig2_tradeoff.png", dpi=300)
plt.close(fig)

os.makedirs("paper", exist_ok=True)
print("✓ fig1_passk + fig2_tradeoff (PDF+PNG 300dpi) → paper/")
for m in sorted(passk, key=lambda x: -passk[x]["1"]):
    print(f"  {META[m][0]:<20} p@1={passk[m]['1']:.2f} p@5={passk[m]['5']:.2f} tps={tps_mean.get(m,0):.1f}")
