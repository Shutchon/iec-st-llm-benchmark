#!/usr/bin/env python3
"""RQ4: Failure-mode taxonomy จาก benchmark_results.jsonl
แหล่ง: error_category (หลัก) + compiler_log (ย่อย) + ตรวจ generated_st_code (ภาษาถิ่น)
ผลลัพธ์: taxonomy.json + ตารางสรุป"""
import json, re
from collections import defaultdict, Counter

rows = [json.loads(l) for l in open("benchmark_results.jsonl", encoding="utf-8")]

def subcategorize(r):
    cat = r.get("error_category", "None")
    code = (r.get("generated_st_code") or "")
    log = (r.get("compiler_log") or "").lower()
    up = code.upper()
    if cat == "Empty_Response":
        return "Empty_Response"
    if cat == "Generation_Error":
        return "Generation_Error"
    if cat == "None":
        return "PASS"
    # ภาษาถิ่น (ตรวจจากโค้ดจริง แม้ error ไปโผล่หมวด syntax)
    if "END_METHOD" in up or re.search(r"\bMETHOD\s+\w+", up):
        return "Dialect_OO_METHOD"
    if re.search(r"\bBEGIN\b", up):
        return "Dialect_SCL_BEGIN"
    if "expecting end_function_block before end of file" in log or (
        "FUNCTION_BLOCK" in up and "END_FUNCTION_BLOCK" not in up):
        return "Missing_END_FUNCTION_BLOCK"
    if re.search(r"^[^\n]*//", code, re.M) or "//" in code.split("FUNCTION_BLOCK")[0]:
        pass  # // ตรวจด้านล่างแบบเจาะจง
    if any(l.strip().startswith("//") for l in code.splitlines()):
        return "C_Style_Comment"
    if "';' missing" in log or "missing at the end of statement" in log:
        return "Missing_Semicolon"
    if "end_var" in log:
        return "VAR_Block_Error"
    if "type incompatib" in log or "type mismatch" in log:
        return "Type_Mismatch"
    if "undeclared" in log or "unknown symbol" in log:
        return "Undeclared_Variable"
    if "no body defined" in log:
        return "Empty_Body"
    if "syntax error" in log or "invalid" in log:
        return "Other_Syntax"
    return "Other"

# ── 1) taxonomy matrix: model × subcategory ──
tax = defaultdict(Counter)
total = Counter()
for r in rows:
    sub = subcategorize(r)
    tax[r["model"]][sub] += 1
    total[sub] += 1

ORDER = ["PASS", "Empty_Response", "Dialect_OO_METHOD", "Dialect_SCL_BEGIN",
         "C_Style_Comment", "Missing_Semicolon", "Missing_END_FUNCTION_BLOCK", "VAR_Block_Error",
         "Type_Mismatch", "Undeclared_Variable", "Empty_Body",
         "Other_Syntax", "Other", "Generation_Error"]
print("── Taxonomy (จำนวน trial จาก 450 ต่อโมเดล) ──")
hdr = f"{'model':<24}" + "".join(f"{s[:9]:>10}" for s in ORDER if s in total)
print(hdr)
for m in sorted(tax):
    print(f"{m:<24}" + "".join(f"{tax[m].get(s,0):>10}" for s in ORDER if s in total))
print(f"{'TOTAL':<24}" + "".join(f"{total[s]:>10}" for s in ORDER if s in total))

# ── 2) Empty/truncation ตามกลยุทธ์ ──
print("\n── Empty_Response ต่อโมเดล×กลยุทธ์ (จาก 150) + truncation% ──")
et = defaultdict(Counter)
tr = defaultdict(list)
for r in rows:
    if r.get("error_category") == "Empty_Response":
        et[r["model"]][r["strategy"]] += 1
    if r.get("status") == "ok":
        tr[r["model"]].append(r.get("eval_count", 0) >= 2395)
for m in sorted(et):
    trp = sum(tr[m])/len(tr[m])*100 if tr[m] else 0
    print(f"{m:<24} zero={et[m]['zero_shot']:>3} few={et[m]['few_shot']:>3} cot={et[m]['cot']:>3} | trunc={trp:.0f}%")

# ── 3) CoT degradation: เทียบหมวด error zero vs cot ของ qwen3-coder + gemma4 ──
for m in ("qwen3-coder:30b", "gemma4:12b"):
    print(f"\n── {m}: subcategory zero_shot vs cot ──")
    a, b = Counter(), Counter()
    for r in rows:
        if r["model"] != m: continue
        s = subcategorize(r)
        (a if r["strategy"] == "zero_shot" else b if r["strategy"] == "cot" else Counter()) [s] += 1 if r["strategy"] in ("zero_shot","cot") else 0
    keys = sorted(set(a) | set(b))
    for k in keys:
        print(f"  {k:<26} zero={a.get(k,0):>3}  cot={b.get(k,0):>3}")

json.dump({m: dict(c) for m, c in tax.items()}, open("taxonomy.json", "w"), indent=1)
print("\n→ taxonomy.json เขียนแล้ว")
