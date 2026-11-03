#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Level-2 Functional Verification Harness (scan-cycle simulation)
==============================================================
หลักการ: นำ FB ที่ถูกทดสอบ (ground truth หรือผลจาก LLM) ไปห่อด้วย
PROGRAM + CONFIGURATION → คอมไพล์ด้วย MatIEC เป็น C → คอมไพล์ด้วย clang
พร้อม driver ที่คุมเวลาเสมือน (__CURRENT_TIME) → เดินรอบสแกนตาม
truth tables ใน benchmark/tasks.json

โปรโตคอลของ binary (stdin/stdout):
  SCENARIO                 → config_init__() (state ใหม่, globals = 0)
  SET <var> <value>        → ตั้งค่า input global (scalar/TIME)
  SET <var> <idx> <value>  → ตั้งค่าสมาชิกอาร์เรย์
  RUN <cycles> <dt_ms>     → เดินเวลาเสมือน cycles รอบ แล้วพิมพ์
                             VAL <var> <v> ทุกตัว + END
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
IEC2C = os.path.join(ROOT, "tools", "matiec", "iec2c")
IECLIB = os.path.join(ROOT, "tools", "matiec", "lib")
IECC = os.path.join(IECLIB, "C")
CACHE_DIR = os.path.join(ROOT, ".level2_cache")
CC = os.environ.get("CC", "cc")

# ── การแมปชนิดข้อมูล IEC → C ────────────────────────────────────────────────
SCALARS = {
    "BOOL":  {"c": "BOOL",  "fmt": "%d",          "scan": "%d",   "cast": "int"},
    "INT":   {"c": "INT",   "fmt": "%d",          "scan": "%d",   "cast": "int"},
    "DINT":  {"c": "DINT",  "fmt": "%d",          "scan": "%d",   "cast": "int"},
    "REAL":  {"c": "REAL",  "fmt": "%.9g",        "scan": "%lf",  "cast": "double"},
    "LREAL": {"c": "LREAL", "fmt": "%.17g",       "scan": "%lf",  "cast": "double"},
    "BYTE":  {"c": "BYTE",  "fmt": "%u",          "scan": "%u",   "cast": "unsigned"},
    "WORD":  {"c": "WORD",  "fmt": "%u",          "scan": "%u",   "cast": "unsigned"},
    "DWORD": {"c": "DWORD", "fmt": "%u",          "scan": "%u",   "cast": "unsigned"},
    "TIME":  {"c": "TIME",  "fmt": "%lld",        "scan": "%lld", "cast": "long long"},
}
ARR_RE = re.compile(r"^ARRAY\s*\[\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*\]\s*OF\s*([A-Z]+)$", re.I)
DECL_RE = re.compile(r"(:\s*)ARRAY\s*\[\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*\]\s*OF\s*([A-Za-z_]\w*)\s*;", re.I)


def parse_type(ts: str):
    m = ARR_RE.match(ts.strip())
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return {"kind": "array", "lo": lo, "hi": hi, "base": m.group(3).upper()}
    return {"kind": "scalar", "base": ts.strip().upper()}


def type_name(t):
    if t["kind"] == "scalar":
        return t["base"]
    neg = lambda n: f"m{abs(n)}" if n < 0 else str(n)
    return f"Arr{neg(t['lo'])}t{neg(t['hi'])}_{t['base']}"


# ── สร้าง wrapper ST ────────────────────────────────────────────────────────
def transform_fb_code(st_code: str, named_types: dict):
    """เปลี่ยนการประกาศ ARRAY แบบ anonymous เป็น named type (MatIEC บังคับ)"""
    def repl(m):
        lo, hi, base = int(m.group(2)), int(m.group(3)), m.group(4).upper()
        key = (lo, hi, base)
        if key not in named_types:
            named_types[key] = True
        return f"{m.group(1)}{type_name({'kind':'array','lo':lo,'hi':hi,'base':base})};"
    return DECL_RE.sub(repl, st_code)


def build_wrapper_st(task, st_code):
    fb_name = None
    m = re.search(r"FUNCTION_BLOCK\s+([A-Za-z_]\w*)", st_code, re.I)
    if not m:
        raise ValueError("ไม่พบ FUNCTION_BLOCK ในโค้ด")
    fb_name = m.group(1)
    named = {}
    code = transform_fb_code(st_code, named)

    io_vars = ([("in", v) for v in task["inputs"]]
               + [("out", v) for v in task["outputs"]]
               + [("io", v) for v in task.get("io_vars", [])])
    typed = []
    for _, v in io_vars:
        t = parse_type(v["type"])
        if t["kind"] == "array" and (t["lo"], t["hi"], t["base"]) not in named:
            named[(t["lo"], t["hi"], t["base"])] = True
        typed.append(t)

    type_block = ""
    if named:
        lines = ["TYPE"]
        for (lo, hi, base) in named:
            lines.append(f"    {type_name({'kind':'array','lo':lo,'hi':hi,'base':base})} : ARRAY[{lo}..{hi}] OF {base};")
        type_block = "\n".join(lines) + "\nEND_TYPE\n"

    ext, glob, args = [], [], []
    for (kind, v), t in zip(io_vars, typed):
        gname = f"G_{v['name']}"
        decl = f"    {gname} : {type_name(t)};"
        ext.append(decl); glob.append(decl)
        if kind == "in" or kind == "io":
            args.append(f"{v['name']} := {gname}")
        else:
            args.append(f"{v['name']} => {gname}")

    return f"""{type_block}{code}

PROGRAM TestMain
VAR_EXTERNAL
{chr(10).join(ext)}
END_VAR
VAR
    fb : {fb_name};
END_VAR
    fb({', '.join(args)});
END_PROGRAM

CONFIGURATION Cfg
VAR_GLOBAL
{chr(10).join(glob)}
END_VAR
RESOURCE Res ON SINGLE
    TASK Fast(INTERVAL := T#100ms, PRIORITY := 1);
    PROGRAM Main WITH Fast : TestMain;
END_RESOURCE
END_CONFIGURATION
"""


# ── สร้าง driver C ──────────────────────────────────────────────────────────
def build_driver_c(task):
    io_vars = ([("in", v) for v in task["inputs"]]
               + [("out", v) for v in task["outputs"]]
               + [("io", v) for v in task.get("io_vars", [])])
    set_cases, dump_lines, externs = [], [], []
    for kind, v in io_vars:
        t = parse_type(v["type"])
        g = f"G_{v['name']}".upper()
        stor = f"CFG__{g}"
        if t["kind"] == "scalar":
            c = SCALARS[t["base"]]
            externs.append(f"extern __IEC_{t['base']}_t {stor};")
            if t["base"] == "TIME":
                set_cases.append(f'if(!strcmp(name,"{g}")){{ long long ms; if(sscanf(val,"%lld",&ms)!=1) return 1; {stor}.value.tv_sec = ms/1000; {stor}.value.tv_nsec = (int32_t)((ms%1000)*1000000); }}')
                dump_lines.append(f'    printf("VAL {g} %lld\\n", (long long)({stor}.value.tv_sec*1000 + {stor}.value.tv_nsec/1000000));')
            else:
                set_cases.append(f'if(!strcmp(name,"{g}")){{ {c["cast"]} x; if(sscanf(val,"{c["scan"]}",&x)!=1) return 1; {stor}.value = x; }}')
                dump_lines.append(f'    printf("VAL {g} {c["fmt"]}\\n", {stor}.value);')
        else:
            c = SCALARS[t["base"]]
            externs.append(f"extern __IEC_{type_name(t).upper()}_t {stor};")
            set_cases.append(f'if(!strcmp(name,"{g}")){{ int ix; {c["cast"]} x; if(sscanf(val,"%d {c["scan"]}",&ix,&x)!=2 || ix<{t["lo"]} || ix>{t["hi"]}) return 1; {stor}.value.table[ix-{t["lo"]}].value = x; }}')
            for i in range(t["lo"], t["hi"] + 1):
                dump_lines.append(f'    printf("VAL {g}[{i}] {c["fmt"]}\\n", {stor}.value.table[{i - t["lo"]}].value);')
    set_chain = " else ".join(set_cases) if set_cases else "(void)0;"

    return f"""#include <stdio.h>
#include <string.h>
#include "iec_std_lib.h"
#include "accessor.h"
#include "POUS.h"

extern void config_init__(void);
extern void config_run__(unsigned long tick);
TIME __CURRENT_TIME;
{chr(10).join(externs)}

static unsigned long long vtime_ns = 0;
static unsigned long tick = 0;

static int do_set(const char *name, const char *val) {{
    (void)name; (void)val;
    {set_chain}
    else {{ fprintf(stderr, "unknown var %s\\n", name); return 1; }}
    return 0;
}}

static void dump(void) {{
{chr(10).join(dump_lines) if dump_lines else "    (void)0;"}
    printf("END\\n"); fflush(stdout);
}}

int main(void) {{
    char line[512], name[128], val[384];
    config_init__();
    while (fgets(line, sizeof line, stdin)) {{
        if (line[0]=='S' && !strncmp(line, "SCENARIO", 8)) {{
            config_init__();
            printf("OK SCENARIO\\n"); fflush(stdout);
        }} else if (line[0]=='S' && sscanf(line, "SET %127s %383[^\\n]", name, val) == 2) {{
            char *nl = strchr(val, '\\n'); if (nl) *nl = 0;
            if (do_set(name, val)) return 2;
            printf("OK SET\\n"); fflush(stdout);
        }} else if (line[0]=='R') {{
            long cycles; long long dt_ms;
            if (sscanf(line, "RUN %ld %lld", &cycles, &dt_ms) != 2) return 3;
            for (long i = 0; i < cycles; i++) {{
                vtime_ns += (unsigned long long)dt_ms * 1000000ULL;
                __CURRENT_TIME.tv_sec  = (int64_t)(vtime_ns / 1000000000ULL);
                __CURRENT_TIME.tv_nsec = (int32_t)(vtime_ns % 1000000000ULL);
                config_run__(tick++);
            }}
            dump();
        }}
    }}
    return 0;
}}
"""


# ── คอมไพล์ (แคชตาม hash) ─────────────────────────────────────────────────
def compile_harness(task, st_code: str):
    key = hashlib.sha256((task["id"] + "\x00" + st_code).encode()).hexdigest()[:16]
    binpath = os.path.join(CACHE_DIR, f"{key}.bin")
    if os.path.exists(binpath):
        return binpath, None
    work = tempfile.mkdtemp(prefix="lvl2_")
    try:
        wrapper = build_wrapper_st(task, st_code)
        with open(os.path.join(work, "wrapper.st"), "w") as f:
            f.write(wrapper)
        r = subprocess.run([IEC2C, "-I", IECLIB, os.path.join(work, "wrapper.st")],
                           cwd=work, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None, f"iec2c_wrapper_fail: {r.stderr.strip()[:300]}"
        with open(os.path.join(work, "driver.c"), "w") as f:
            f.write(build_driver_c(task))
        r = subprocess.run([CC, "-fcommon", "-O1", "-w",
                            "-I", work, "-I", IECC,
                            os.path.join(work, "driver.c"),
                            os.path.join(work, "Cfg.c"),
                            os.path.join(work, "Res.c"),
                            "-lm", "-o", os.path.join(work, "bin")],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return None, f"clang_fail: {r.stderr.strip()[:300]}"
        os.makedirs(CACHE_DIR, exist_ok=True)
        shutil.copy(os.path.join(work, "bin"), binpath)
        return binpath, None
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ── รัน tests ───────────────────────────────────────────────────────────────
def _fmt_set(t, v):
    if t["kind"] == "scalar":
        if t["base"] == "BOOL":
            return "1" if v else "0"
        if t["base"] == "TIME":
            return str(int(v))
        return str(v)
    return " ".join(str(x) for x in v)  # ไม่ใช้ทางนี้ (สมาชิกแยก SET)


def _norm(s):
    if isinstance(s, float):
        return round(s, 9)
    return s


def run_tests(task, st_code: str, timeout_s: int = 20):
    """คืน {'all_passed': bool, 'scenarios': [{'name','passed','failed_at','detail'}]}"""
    binpath, err = compile_harness(task, st_code)
    if binpath is None:
        return {"all_passed": False, "harness_error": err,
                "scenarios": [{"name": s["name"], "passed": False, "failed_at": 0,
                               "detail": err} for s in task.get("tests", [])]}

    inmap = {v["name"]: parse_type(v["type"]) for v in task["inputs"]}
    iomap = {v["name"]: parse_type(v["type"]) for v in task.get("io_vars", [])}
    results = []
    p = subprocess.Popen([binpath], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)
    try:
        for sc in task.get("tests", []):
            p.stdin.write("SCENARIO\n"); p.stdin.flush(); p.stdout.readline()
            sticky_in = {}
            passed, failed_at, detail = True, 0, ""
            for si, step in enumerate(sc["steps"], 1):
                sticky_in.update(step.get("in", {}))
                step_io = step.get("io", {})   # VAR_IN_OUT ไม่ sticky: เป็น state สองทาง
                for n, v in sticky_in.items():
                    t = inmap[n]
                    if t["kind"] == "array":
                        for idx, x in enumerate(v):
                            p.stdin.write(f"SET G_{n.upper()} {t['lo'] + idx} {1 if (t['base']=='BOOL' and x) else x}\n")
                    else:
                        p.stdin.write(f"SET G_{n.upper()} {_fmt_set(t, v)}\n")
                for n, v in step_io.items():
                    t = iomap[n]
                    if t["kind"] == "array":
                        for idx, x in enumerate(v):
                            p.stdin.write(f"SET G_{n.upper()} {t['lo'] + idx} {1 if (t['base']=='BOOL' and x) else x}\n")
                    else:
                        p.stdin.write(f"SET G_{n.upper()} {_fmt_set(t, v)}\n")
                p.stdin.write(f"RUN {step.get('cycles', 1)} {step.get('dt_ms', 100)}\n")
                p.stdin.flush()
                vals, ok_ack = {}, 0
                while True:
                    ln = p.stdout.readline()
                    if not ln or ln.startswith("END"):
                        break
                    if ln.startswith("OK "):
                        ok_ack += 1; continue
                    parts = ln.split()
                    if len(parts) >= 3 and parts[0] == "VAL":
                        vals[parts[1]] = parts[2] if len(parts) == 3 else " ".join(parts[2:])
                # ── เทียบ ──
                def cmp():
                    for var, exp in step.get("expect", {}).items():
                        got = vals.get(f"G_{var}" if not isinstance(exp, list) else None) if False else None
                        key = f"G_{var}".upper()
                        if isinstance(exp, list):
                            for i, e in enumerate(exp):
                                g = vals.get(f"{key}[{inmap_iomap(task, var)[0] + i}]")
                                if g is None or _norm(float(g) if not isinstance(e, bool) else int(g)) != _norm(e):
                                    return f"expect {var}[{i}]: got '{g}' want '{e}'"
                        else:
                            g = vals.get(key)
                            if isinstance(exp, bool):
                                if g != ("1" if exp else "0"):
                                    return f"expect {var}: got '{g}' want {exp}"
                            elif g is None or _norm(float(g)) != _norm(exp):
                                return f"expect {var}: got '{g}' want '{exp}'"
                    for var, spec in step.get("expect_approx", {}).items():
                        g = vals.get(f"G_{var}".upper())
                        if g is None or abs(float(g) - spec["value"]) > spec["tol"]:
                            return f"approx {var}: got '{g}' want ~{spec['value']}±{spec['tol']}"
                    for var, spec in step.get("expect_time", {}).items():
                        g = vals.get(f"G_{var}".upper())
                        if g is None or abs(int(float(g)) - spec["ms"]) > spec["tol_ms"]:
                            return f"time {var}: got '{g}' ms want ~{spec['ms']}±{spec['tol_ms']}ms"
                    return None
                prob = cmp()
                if prob:
                    passed, failed_at, detail = False, si, prob
                    break
            results.append({"name": sc["name"], "passed": passed,
                            "failed_at": failed_at, "detail": detail})
    finally:
        try:
            p.stdin.close(); p.terminate(); p.wait(timeout=3)
        except Exception:
            pass
    return {"all_passed": all(r["passed"] for r in results) and bool(results), "scenarios": results}


def inmap_iomap(task, var):
    for v in task["inputs"] + task.get("io_vars", []):
        if v["name"] == var:
            return parse_type(v["type"])["lo"], None
    for v in task["outputs"]:
        if v["name"] == var:
            return parse_type(v["type"])["lo"], None
    return 0, None


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tasks = json.load(open(os.path.join(ROOT, "benchmark", "tasks.json"), encoding="utf-8"))
    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        n_pass = 0
        for t in tasks:
            res = run_tests(t, t["ground_truth"])
            mark = "✓" if res["all_passed"] else "✗"
            if res["all_passed"]:
                n_pass += 1
            else:
                for s in res["scenarios"]:
                    if not s["passed"]:
                        print(f"  {mark} {t['id']} [{s['name']}] failed@step{s['failed_at']}: {s['detail'][:110]}")
            print(f"{mark} {t['id']} {t['title']}")
        print(f"\nผ่าน {n_pass}/{len(tasks)}")
        sys.exit(0 if n_pass == len(tasks) else 1)
