# IEC-ST-30 Benchmark Dataset

ชุดโจทย์ 30 ข้อ (Basic/Intermediate/Advanced อย่างละ 10) สำหรับประเมินการสร้างโค้ด IEC 61131-3 Structured Text

## ไฟล์
- **`tasks.json`** — แหล่งความจริง (source of truth) ของ dataset: ข้อกำหนดโจทย์ + I/O spec + ground-truth ST code + **truth tables (tests)** สำหรับ Level-2 functional verification
- `task_definitions.py` — โค้ดต้นทางของส่วนที่แก้ไข/เพิ่ม (fixes, โจทย์ใหม่ 4 ข้อ, tests ทั้งหมด)
- `_extracted26.json` — ผลแยกจากเอกสารเดิม (intermediate artifact)
- `../IEC 61131-3 ST 30-Task Benchmark Dataset Suite.md` — เอกสารเดิมจากแผนเก่า (เก็บไว้อ้างอิง)

## การสร้างใหม่ / ตรวจสอบ
```bash
python3 tools/parse_legacy_dataset.py   # แยก 26 ข้อจากเอกสารเดิม
python3 tools/build_tasks_json.py       # รวม + ตรวจ (ต้องผ่าน 30/30 + schema)
```

## สิ่งที่แก้จากเอกสารต้นฉบับ (บันทึก 2026-10-19)
1. เติมโจทย์ที่ขาด: **T05** (TOF), **T12** (DOL starter), **T14** (Conveyor sorting), **T18** (Bottle filling) → ครบ 10/10/10
2. แก้ ground truth ที่คอมไพล์ไม่ผ่าน MatIEC:
   - T16: `Step` เป็นคำสงวน (SFC) → `Phase`
   - T22: `Integral`/`Derivative` ทำให้ MatIEC เกิด error → `IntAccum`/`Deriv`
   - T29: `SHR`/`AND` กับ INT ผิดมาตรฐาน (ต้องเป็น ANY_BIT) → แปลงผ่าน WORD
   - 7 ข้อเกิดจาก escape `\_` `\+` ของ Google Docs export
3. แก้ metadata I/O: T20 (`Out` เป็น VAR_IN_OUT), T26 (ประกาศ input รวมบรรทัด)
4. **เพิ่ม truth tables ครบ 30 ข้อ** (เดิมไม่มีเลย)

## รูปแบบ tests (สำหรับ Level-2 harness — ยังต้อง implement)
แต่ละ scenario = FB instance ใหม่; แต่ละ step: ตั้ง input/io แบบ sticky → เดิน `cycles` รอบสแกน × `dt_ms` → ตรวจผลหลังรอบสุดท้าย:
- `expect` — ค่าเท่ากันเป๊ะ (BOOL/INT/BYTE/array)
- `expect_approx` — `{var: {value, tol}}` สำหรับ REAL
- `expect_time` — `{var: {ms, tol_ms}}` สำหรับ TIME
- input ชนิด TIME ให้เป็นจำนวน ms

⚠️ **สถานะ:** Level-2 harness (`tools/level2_harness.py`) **implement และ validate แล้ว (2026-10-30)** — ground truth ทั้ง 30 ผ่าน truth tables ของตัวเอง (30/30) ผ่านการจำลอง scan-cycle ด้วยเวลาเสมือน (`__CURRENT_TIME`) + negative cases (ตรรกะผิด/interface ผิด) ถูกจับได้ถูกต้อง · แก้ไขค่าคาดหวังเดิม 6 จุดที่คำนวณพรมแดนเวลาคลาด (T02/T07×2/T16/T21) และเลขผิด 1 จุด (T25) — ดูประวัติใน git ของ task_definitions.py
