#!/usr/bin/env python3
"""
================================================================================
LAB Experiment Pipeline v2 — Local LLM Evaluation for IEC 61131-3 ST Codegen
================================================================================
แก้ไขจากรุ่นเดิม (plc_llm_benchmark_lab.py.txt) ตาม readiness check 2026-10-19:
  1. ตัด _mock_response และ _fallback_syntax_check ออกทั้งหมด
     (เดิมหาก Ollama/iec2c ล้ม จะแอบใส่ผลลัพธ์ปลอม → ปนเปื้อนข้อมูลวิจัย)
     ตอนนี้ fail-hard: บันทึก status และนับเป็นความล้มเหลวของ trial
  2. Roster 8 โมเดลตาม revised_plan_iece.md พร้อม metadata (tier/arch/think)
  3. คุมงบเวลา: num_predict=800 + ปิด thinking mode ของโมเดลที่รองรับ
  4. เรียก iec2c ด้วย absolute path + -I lib (ตาม tools/BUILD_NOTES.md)
  5. โหลดโจทย์จาก benchmark/tasks.json (30 ข้อ + truth tables)
  6. เพิ่ม hook สำหรับ Level-2 functional verification (รอ harness)
วิธีใช้:
  python3 plc_llm_benchmark_lab.py                          # รันเต็ม 8×3×30×5
  python3 plc_llm_benchmark_lab.py --models gemma4:12b --tasks T01 --runs 1
  python3 plc_llm_benchmark_lab.py --strategies zero_shot --runs 1 --tasks T01,T02
================================================================================
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(ROOT, "benchmark", "tasks.json")
IEC2C = os.path.join(ROOT, "tools", "matiec", "iec2c")
IECLIB = os.path.join(ROOT, "tools", "matiec", "lib")
TEMP_ST_DIR = os.path.join(ROOT, "temp_st_compile")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")

# ── Roster 8 โมเดล (revised_plan_iece.md §2) ─────────────────────────────────
# think=True → ส่ง "think": false ให้ Ollama (โมเดลที่มี thinking mode)
ROSTER = [
    {"tag": "qwen3-coder:30b",      "display": "Qwen3-Coder-30B-A3B", "tier": "A", "arch": "moe",  "family": "qwen", "think": True},
    {"tag": "gpt-oss:20b",          "display": "GPT-OSS-20B",         "tier": "A", "arch": "moe",  "family": "openai", "think": "low"},
    {"tag": "qwen3.8:27b",          "display": "Qwen3.8-27B",         "tier": "A", "arch": "dense", "family": "qwen", "think": True},
    {"tag": "qwen3.5:27b",          "display": "Qwen3.5-27B",         "tier": "A", "arch": "moe",  "family": "qwen", "think": True},
    {"tag": "gemma4:12b",           "display": "Gemma4-12B",          "tier": "A", "arch": "dense", "family": "google", "think": True},
    {"tag": "qwen2.5-coder:14b",    "display": "Qwen2.5-Coder-14B",   "tier": "B", "arch": "dense", "family": "qwen", "think": False},
    {"tag": "deepseek-coder-v2:16b", "display": "DeepSeek-Coder-V2-Lite", "tier": "B", "arch": "moe", "family": "deepseek", "think": False},
    {"tag": "llama3.1:8b",          "display": "Llama-3.1-8B",        "tier": "B", "arch": "dense", "family": "meta", "think": False},
]

NUM_PREDICT = 2400         # แคปรุ่นสูง (F-12): gpt-oss คิดไม่ปิดได้ ~1900+200; โมเดลที่หยุดเองไม่กระทบ
TEMPERATURE = 0.2          # หมายเหตุ: ค่านี้จะ lock ตอน protocol freeze (ดูแผน สัปดาห์ 4–5)
GEN_TIMEOUT_S = 1200       # รวมเวลาโหลดโมเดลครั้งแรก
STRATEGIES = ["zero_shot", "few_shot", "cot"]

SYSTEM_INSTRUCTION = (
    "You are an expert industrial automation engineer specializing in PLC programming.\n"
    "Generate syntactically correct IEC 61131-3 Structured Text (ST) code enclosed in a ```st ... ``` block.\n"
    "Declare all variables strictly using VAR_INPUT, VAR_OUTPUT, or VAR blocks within a FUNCTION_BLOCK.\n"
    "Output ONLY the code block, no additional explanation."
)


class GenerationError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_URL):
        self.base_url = base_url

    def generate(self, model: str, prompt: str, disable_think: bool) -> Dict:
        """คืน {text, latency_s, tokens_per_s, eval_count, think_disabled} — fail hard เมื่อล้ม"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": NUM_PREDICT, "temperature": TEMPERATURE},
        }
        if disable_think is not None:
            payload["think"] = disable_think  # False = ปิด, "low" = ระดับต่ำสุด (gpt-oss)
        start = time.time()
        r = requests.post(self.base_url, json=payload, timeout=GEN_TIMEOUT_S)
        latency = time.time() - start
        if r.status_code != 200:
            # บางรุ่น server/โมเดลไม่รับพารามิเตอร์ think → ลองอีกครั้งแบบไม่มี think
            if disable_think is not None and "think" in r.text.lower():
                payload.pop("think", None)
                start = time.time()
                r = requests.post(self.base_url, json=payload, timeout=GEN_TIMEOUT_S)
                latency = time.time() - start
                disable_think = False
            if r.status_code != 200:
                raise GenerationError(f"HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        text = data.get("response", "")
        eval_count = data.get("eval_count", 0)
        eval_ns = data.get("eval_duration", 0)
        # fallback (F-11): บางโมเดล Ollama ไม่ส่ง eval_duration → ประมาณจาก latency รวม (แบบ approximate)
        tps = (eval_count / (eval_ns / 1e9)) if eval_ns > 0 else (eval_count / latency if latency > 0 else 0.0)
        return {"text": text, "latency_s": latency, "tokens_per_s": tps,
                "eval_count": eval_count, "think_disabled": disable_think}


class PromptBuilder:
    @staticmethod
    def var_block(task: Dict) -> str:
        lines = ["Inputs:"]
        for v in task["inputs"]:
            lines.append(f"  {v['name']} : {v['type']}")
        lines.append("Outputs:")
        for v in task["outputs"]:
            lines.append(f"  {v['name']} : {v['type']}")
        if task.get("io_vars"):
            lines.append("In_Out:")
            for v in task["io_vars"]:
                lines.append(f"  {v['name']} : {v['type']}")
        return "\n".join(lines)

    @classmethod
    def build(cls, task: Dict, strategy: str) -> str:
        desc = f"Task Title: {task['title']}\nRequirement: {task['requirement']}\n{cls.var_block(task)}\n"
        if strategy == "zero_shot":
            return f"{SYSTEM_INSTRUCTION}\n\n{desc}\nWrite the complete FUNCTION_BLOCK in ST code."
        if strategy == "few_shot":
            example = (
                "Example Task: Basic AND Gate\n"
                "Inputs:\n  bIn1 : BOOL\n  bIn2 : BOOL\nOutputs:\n  bOut : BOOL\n"
                "Expected ST Code:\n"
                "```st\nFUNCTION_BLOCK FB_Example\nVAR_INPUT\n    bIn1 : BOOL;\n    bIn2 : BOOL;\nEND_VAR\n"
                "VAR_OUTPUT\n    bOut : BOOL;\nEND_VAR\n    bOut := bIn1 AND bIn2;\nEND_FUNCTION_BLOCK\n```\n\n"
            )
            return f"{SYSTEM_INSTRUCTION}\n\n{example}{desc}\nWrite the complete FUNCTION_BLOCK in ST code."
        if strategy == "cot":
            cot = (
                "Before writing the ST code, perform this step-by-step reasoning:\n"
                "1. Identify all I/O variables and their IEC data types.\n"
                "2. Analyze state transitions or logical conditions.\n"
                "3. Write the FUNCTION_BLOCK enclosed in ```st ... ```.\n"
            )
            return f"{SYSTEM_INSTRUCTION}\n\n{cot}\n{desc}"
        raise ValueError(strategy)


class STCodeEvaluator:
    @staticmethod
    def extract_st_code(response_text: str) -> str:
        m = re.search(r"```(?:st|iecst|structured ?text)?\s*\n?(.*?)```", response_text, re.DOTALL | re.IGNORECASE)
        if m and "FUNCTION_BLOCK" in m.group(1).upper():
            return m.group(1).strip()
        m = re.search(r"(FUNCTION_BLOCK\b.*?\bEND_FUNCTION_BLOCK)", response_text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return response_text.strip()

    @staticmethod
    def compile_check_matiec(st_code: str, tag: str) -> Tuple[bool, str, str]:
        """คืน (ผ่าน, หมวด error, log) — ไม่มี fallback ปลอม ถ้า iec2c หายถือว่า setup พัง"""
        if not st_code or not st_code.strip():
            return False, "Empty_Response", "(โค้ดที่สกัดได้ว่างเปล่า)"
        if not os.path.exists(IEC2C):
            raise RuntimeError(f"iec2c ไม่พบที่ {IEC2C} — ดู tools/BUILD_NOTES.md")
        path = os.path.join(TEMP_ST_DIR, f"{tag}.st")
        with open(path, "w", encoding="utf-8") as f:
            f.write(st_code)
        r = subprocess.run([IEC2C, "-I", IECLIB, path], capture_output=True, text=True, timeout=30)
        log = (r.stdout + r.stderr).strip()
        if r.returncode == 0:
            return True, "None", log
        return False, STCodeEvaluator.categorize_error(log), log[:2000]

    @staticmethod
    def categorize_error(log: str) -> str:
        low = log.lower()
        if "undeclared" in low or "unknown symbol" in low:
            return "Variable_Declaration_Error"
        if "type incompatib" in low or "type mismatch" in low:
            return "Type_Mismatch_Error"
        if "syntax error" in low or "unexpected" in low or "missing" in low or "invalid" in low:
            return "Syntax_Grammar_Error"
        if "end_function_block" in low or "end_if" in low or "end_var" in low:
            return "Block_Closure_Error"
        return "Other_Compiler_Error"


def verify_functional(task: Dict, st_code: str) -> Tuple[Optional[bool], str]:
    """Level-2: จำลอง scan cycle เทียบ truth table (task['tests'])
    ใช้ tools/level2_harness.py (MatIEC→C + เวลาเสมือน) — validated 30/30 กับ ground truth"""
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        from level2_harness import run_tests
        res = run_tests(task, st_code)
        if res.get("harness_error"):
            return False, f"harness_error: {res['harness_error'][:120]}"
        n_pass = sum(1 for s in res["scenarios"] if s["passed"])
        n_all = len(res["scenarios"]) or 1
        return res["all_passed"], f"{n_pass}/{n_all} scenarios passed"
    except Exception as e:
        return None, f"harness_exception: {str(e)[:120]}"


def run(models: List[Dict], tasks: List[Dict], strategies: List[str], runs: int, out_file: str) -> None:
    client = OllamaClient()
    os.makedirs(TEMP_ST_DIR, exist_ok=True)
    done = set()
    if os.path.exists(out_file):
        with open(out_file, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add((r["model"], r["strategy"], r["task_id"], r["run_number"]))
                except json.JSONDecodeError:
                    continue
    total = len(models) * len(strategies) * len(tasks) * runs
    print(f"🚀 Benchmark | models={len(models)} strategies={strategies} tasks={len(tasks)} runs={runs} → {total} trials (เสร็จแล้ว {len(done)})")
    t0 = time.time()
    n_new = 0
    for model in models:
        for strategy in strategies:
            for task in tasks:
                prompt = PromptBuilder.build(task, strategy)
                for run_no in range(1, runs + 1):
                    if (model["tag"], strategy, task["id"], run_no) in done:
                        continue
                    rec = {"model": model["tag"], "model_display": model["display"],
                           "tier": model["tier"], "arch": model["arch"], "family": model["family"],
                           "strategy": strategy, "task_id": task["id"],
                           "complexity": task["complexity"], "run_number": run_no,
                           "num_predict": NUM_PREDICT, "temperature": TEMPERATURE}
                    # ── ขั้น 1: generate ──
                    try:
                        gen = client.generate(model["tag"], prompt, model["think"])
                        rec.update(status="ok", latency_s=round(gen["latency_s"], 3),
                                   tokens_per_s=round(gen["tokens_per_s"], 2),
                                   eval_count=gen["eval_count"], think_disabled=gen["think_disabled"])
                        st_code = STCodeEvaluator.extract_st_code(gen["text"])
                        rec["generated_st_code"] = st_code
                        rec["raw_response_head"] = gen["text"][:400]
                    except Exception as e:  # fail-hard: ไม่มี mock
                        rec.update(status="gen_error", error=str(e)[:300],
                                   compilation_pass=False, error_category="Generation_Error",
                                   functional_pass=None, functional_note="skipped")
                        _append(out_file, rec); n_new += 1
                        continue
                    # ── ขั้น 2: compile (Level 1) ──
                    try:
                        ok, cat, log = STCodeEvaluator.compile_check_matiec(st_code, f"{task['id']}_{run_no}")
                        rec.update(compilation_pass=ok, error_category=cat, compiler_log=log[:500])
                    except Exception as e:
                        rec.update(compilation_pass=False, error_category="Execution_Error", error=str(e)[:300])
                    # ── ขั้น 3: functional (Level 2 — hook) ──
                    fpass, fnote = verify_functional(task, st_code)
                    rec.update(functional_pass=fpass, functional_note=fnote)
                    _append(out_file, rec); n_new += 1
                    print(f"  [{int(time.time()-t0)}s] {model['tag']} × {strategy} × {task['id']} #{run_no}: "
                          f"compile={'✓' if rec['compilation_pass'] else '✗'} ({rec['error_category']})", flush=True)
    print(f"เสร็จ: เพิ่ม {n_new} trial ใหม่ → {out_file}")


def _append(out_file: str, rec: Dict) -> None:
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", help="comma-separated tags (default: ทั้ง roster 8)")
    ap.add_argument("--tasks", help="comma-separated ids เช่น T01,T02 (default: ทั้ง 30)")
    ap.add_argument("--strategies", default=",".join(STRATEGIES))
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default=os.path.join(ROOT, "benchmark_results.jsonl"))
    a = ap.parse_args()
    if not os.path.exists(TASKS_FILE):
        sys.exit(f"ไม่พบ {TASKS_FILE} — รัน tools/build_tasks_json.py ก่อน")
    tasks = json.load(open(TASKS_FILE, encoding="utf-8"))
    if a.tasks:
        want = {t.strip() for t in a.tasks.split(",")}
        tasks = [t for t in tasks if t["id"] in want]
        miss = want - {t["id"] for t in tasks}
        if miss: sys.exit(f"ไม่มีโจทย์: {sorted(miss)}")
    models = ROSTER if not a.models else [m for m in ROSTER if m["tag"] in set(a.models.split(","))]
    if not models: sys.exit("ไม่มีโมเดลที่ระบุใน roster")
    run(models, tasks, a.strategies.split(","), a.runs, a.out)


if __name__ == "__main__":
    main()
