#!/usr/bin/env python3
"""รวม dataset ฉบับสมบูรณ์ → benchmark/tasks.json
ตรวจสอบ 2 ชั้น: (1) ground truth ทั้ง 30 ต้องคอมไพล์ผ่าน MatIEC (2) tests อ้างตัวแปรถูกต้อง"""
import json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "benchmark"))
from task_definitions import GROUND_TRUTH_FIXES, IO_FIXES, NEW_TASKS, TESTS  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
EXTRACTED = os.path.join(ROOT, "benchmark", "_extracted26.json")
OUT = os.path.join(ROOT, "benchmark", "tasks.json")
IEC2C = os.path.join(ROOT, "tools", "matiec", "iec2c")
IECLIB = os.path.join(ROOT, "tools", "matiec", "lib")

def compile_st(code: str, tag: str) -> tuple:
    with tempfile.NamedTemporaryFile("w", suffix=".st", delete=False, dir=ROOT) as f:
        f.write(code); path = f.name
    try:
        r = subprocess.run([IEC2C, "-I", IECLIB, path], capture_output=True, text=True, timeout=20)
        err = "\n".join(l for l in r.stderr.splitlines() if l.strip())[:200]
        return r.returncode == 0, err
    finally:
        os.unlink(path)
        for extra in os.listdir(ROOT):
            if extra.startswith(("POUS", "LOC", "GLOBALS")) and extra.endswith((".c", ".h")):
                os.unlink(os.path.join(ROOT, extra))

def array_len(type_str: str):
    m = re.search(r"ARRAY\[(\d+)\.\.(\d+)\]", type_str or "")
    return (int(m.group(2)) - int(m.group(1)) + 1) if m else None

def validate_tests(task, errors):
    out_ok = {v["name"]: v["type"] for v in task["outputs"]}
    io_ok = {v["name"]: v["type"] for v in task.get("io_vars", [])}
    in_ok = {v["name"]: v["type"] for v in task["inputs"]}
    for sc in task.get("tests", []):
        for si, step in enumerate(sc["steps"]):
            for var in step.get("in", {}):
                if var not in in_ok:
                    errors.append(f"{task['id']}/{sc['name']}#s{si}: in '{var}' ไม่มีใน VAR_INPUT")
            for var, val in step.get("io", {}).items():
                if var not in io_ok:
                    errors.append(f"{task['id']}/{sc['name']}#s{si}: io '{var}' ไม่มีใน VAR_IN_OUT")
                n = array_len(io_ok.get(var, ""))
                if n and not isinstance(val, list): errors.append(f"{task['id']}: io '{var}' ต้องเป็น list")
            for op in ("expect",):
                for var, val in step.get(op, {}).items():
                    if var not in out_ok and var not in io_ok:
                        errors.append(f"{task['id']}/{sc['name']}#s{si}: expect '{var}' ไม่มีใน output/io")
                        continue
                    n = array_len(out_ok.get(var) or io_ok.get(var) or "")
                    if n is not None and (not isinstance(val, list) or len(val) != n):
                        errors.append(f"{task['id']}/{sc['name']}#s{si}: expect '{var}' ต้องเป็น list ยาว {n}")
            for var in step.get("expect_approx", {}):
                if var not in out_ok and var not in io_ok:
                    errors.append(f"{task['id']}/{sc['name']}#s{si}: approx '{var}' ไม่มีใน output/io")
            for var in step.get("expect_time", {}):
                if var not in out_ok and var not in io_ok:
                    errors.append(f"{task['id']}/{sc['name']}#s{si}: time '{var}' ไม่มีใน output/io")

def main():
    tasks = json.load(open(EXTRACTED, encoding="utf-8"))
    for t in tasks:
        if t["id"] in IO_FIXES: t.update(IO_FIXES[t["id"]])
        if t["id"] in GROUND_TRUTH_FIXES: t["ground_truth"] = GROUND_TRUTH_FIXES[t["id"]]
    tasks += [dict(nt) for nt in NEW_TASKS]
    tasks.sort(key=lambda t: t["id"])
    for t in tasks: t["tests"] = TESTS.get(t["id"], [])

    # ── ชั้น 1: คอมไพล์ ground truth ทั้งหมด ──
    compile_fail = []
    for t in tasks:
        ok, err = compile_st(t["ground_truth"], t["id"])
        if not ok: compile_fail.append((t["id"], err))
    # ── ชั้น 2: schema ของ tests ──
    schema_err = []
    for t in tasks: validate_tests(t, schema_err)
    missing = [t["id"] for t in tasks if not t["tests"]]

    json.dump(tasks, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    n_by_cx = {}
    for t in tasks: n_by_cx[t["complexity"]] = n_by_cx.get(t["complexity"], 0) + 1
    print(f"รวม {len(tasks)} โจทย์ → {OUT} | ตามระดับ: {n_by_cx}")
    print(f"คอมไพล์ผ่าน: {len(tasks)-len(compile_fail)}/{len(tasks)}")
    for tid, err in compile_fail: print(f"  ✗ {tid}: {err}")
    if schema_err:
        print(f"schema ผิด {len(schema_err)} จุด:"); [print(f"  ✗ {e}") for e in schema_err]
    else: print("schema ของ tests: ผ่านทั้งหมด")
    if missing: print(f"⚠️ ไม่มี tests: {missing}")
    return 1 if (compile_fail or schema_err or missing) else 0

if __name__ == "__main__":
    sys.exit(main())
