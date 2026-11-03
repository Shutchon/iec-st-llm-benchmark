# Experimental Protocol (Pre-Registration)
**งานวิจัย:** A Comparative Evaluation of Open-Source Local Large Language Models for IEC 61131-3 Structured Text Code Generation
**สถานะ:** 🔒 **LOCKED v1.0 (2026-11-01)** — pilot ครบ 8/8 ผ่าน QC ทุกโมเดล (F-01–F-14) · ห้ามแก้ระหว่างรันเก็บข้อมูล (เฉพาะ amendment พร้อมเหตุผล)

---

## 1. การออกแบบ

**ปัจจัย:** โมเดล (8) × กลยุทธ์ prompting (3) × โจทย์ (30, ซ้อนใน 3 ระดับความยาก) × รอบทำซ้ำ (5) = **3,600 trials**

### 1.1 โมเดล (ตรึง tag + บันทึก digest ตอน lock)
| # | Ollama tag | Tier | ประเภท | think-control |
|---|---|---|---|---|
| 1 | `qwen3-coder:30b` | A | coder MoE | ปิด |
| 2 | `gpt-oss:20b` | A | open-weight MoE | ปิด |
| 3 | `qwen3.8:27b` | A | general dense | ปิด |
| 4 | `qwen3.5:27b` | A | general MoE | ปิด |
| 5 | `gemma4:12b` | A | general dense | **ปิด** (ยืนยันจาก pilot ว่าเป็น thinking model — F-08) |
| 6 | `qwen2.5-coder:14b` | B | coder dense (2024) | ไม่มี |
| 7 | `deepseek-coder-v2:16b` | B | coder MoE (2024) | ไม่มี |
| 8 | `llama3.1:8b` | B | general dense (2024) | ไม่มี |

### 1.2 กลยุทธ์ prompting (template เต็มอยู่ใน `plc_llm_benchmark_lab.py::PromptBuilder` — คงที่ทุกโมเดล)
- `zero_shot` / `few_shot` (1 ตัวอย่าง AND gate) / `cot` (แจกแจง 3 ขั้นก่อนเขียนโค้ด)
- System instruction ระบุ: ผลลัพธ์เป็น ```st block เท่านั้น, ประกาศตัวแปรใน VAR_INPUT/VAR_OUTPUT ตาม spec โจทย์

### 1.3 พารามิเตอร์ generation (คงที่ทุก trial)
- `temperature = 0.2` (ไม่ fix seed — วัด distribution ของโมเดลจริง; ใช้ 5 runs คำนวณ pass@k)
- `num_predict = 2400` (ยกจาก 800 — **amendment v0.2 ตาม F-12:** gpt-oss ปิด reasoning ไม่ได้จริง ใช้ ~1900 โทเคน คิด+ตอบ; แคปเป็นเพดานไม่ใช่เป้า โมเดลที่หยุดเอง (<300 tok) ไม่กระทบ)
- think-control รายโมเดล: `false` (qwen3.x, gemma4) / **`"low"` (gpt-oss — ค่าเดียวที่หยุด reasoning-loop ได้จริง, F-12b)** / ไม่ส่ง (โมเดลไม่มี thinking)

## 2. การวัดผล (3 ชั้น) และกฎการนับ
1. **Level 1 — Compilation (MatIEC/iec2c):** exit 0 = ผ่าน · **กันของปลอม:** โค้ดว่าง = `Empty_Response` = ไม่ผ่าน (MatIEC ยอม translation unit ว่าง)
2. **Level 2 — Functional (scan-cycle + truth table):** ผ่านเมื่อทุก scenario ของโจทย์ผ่าน (schema ใน `benchmark/tasks.json` — ground truth ผ่าน 30/30)
3. **Level 3 — Efficiency:** latency_s, tokens_per_s ต่อ trial

**กฎการนับ (fail-hard):** `gen_error` (รวม timeout) = ไม่ผ่านทั้งสอง level และเข้าหมวด `Generation_Error` · Level 2 รันเฉพาะเมื่อ Level 1 ผ่าน · functional_pass=False ครอบกรณี wrapper mismatch (interface ไม่ตรง spec)

## 3. สถิติ (กำหนดล่วงหน้า ก่อนเห็นข้อมูลเต็ม)
- **pass@k** (unbiased estimator ของ Chen et al. 2021) จาก n=5 runs ต่อเงื่อนไข, k=1..5 · รายงานหลัก: functional pass@1
- **Friedman test** เทียบข้ามโมเดล (บล็อก = โจทย์) ต่อกลยุทธ์, α=0.05
- **Post-hoc:** Wilcoxon signed-rank แบบจับคู่ + **Bonferroni** (28 คู่ → α=0.0018)
- **Effect size:** Cliff's delta ทุกคู่ (รายงานร่วม p-value ตามแนวทาง SafeLLM4SE)
- **Two-way ANOVA:** โมเดล × กลยุทธ์ และ โมเดล × ระดับความยาก (ตัวแปรตอบ: functional pass ต่อ trial — logistic ตรวจ assumption เสริมถ้า cell เล็ก)
- ซอฟต์แวร์: scipy 1.16, statsmodels 0.14 (บันทึก version ใน Method)

## 4. การควบคุมคุณภาพ (QC gates ก่อน/ระหว่าง/หลัง)
- ก่อนรัน: ground truth ผ่าน MatIEC + truth table 30/30; negative controls (โค้ดผิดตรรกะ/ผิด interface) ต้อง fail
- ระหว่างรัน: checkpoint JSONL ทุก trial + resume; บันทึก `raw_response_head`; `think_disabled` ต่อ trial
- หลังรัน: ตรวจ truncation (eval_count ≥ 795) รายงานสัดส่วนต่อโมเดล; สุ่มตรวจตาคน error taxonomy ≥ 20 ตัวอย่าง/โมเดล

## 5. สิ่งที่ประกาศไว้ล่วงหน้าว่า "ไม่ทำ"
- ไม่ fine-tune/ไม่ prompt-tune ต่อโมเดล (prompt เดียวกันทุกตัว — เสี่ยงเอื้อฝ่ายใดฝ่ายหนึ่งอย่างที่ควบคุมได้)
- ไม่เลือกผล/ไม่รันซ้ำเฉพาะที่ fail; ไม่มี trial ถูกลบ (gen_error ก็นับ)
- ablation "plain-ST hint" (F-07) เป็นภาคผนวก แยกจากผลหลัก

## 6. ประวัติการล็อก
| เวอร์ชัน | วันที่ | เหตุการณ์ |
|---|---|---|
| 0.1 | 2026-10-31 | ร่างจากผล pilot batch 0–3 (รวมบทเรียน F-08: think-gemma, empty-guard) |
| 0.2 | 2026-11-01 | num_predict 800→2400 ตาม F-12 (gpt-oss reasoning ปิดไม่ได้) |
| 0.3 | 2026-11-01 | gpt-oss ใช้ think="low" แทน false (ทดสอบแล้ว reasoning จบ ~370 tok) |
| 🔒 1.0 | 2026-11-01 | ล็อกหลัง pilot ครบ 8/8 + QC (amendments รวม: v0.2 cap 2400, v0.3 think รายโมเดล) |
