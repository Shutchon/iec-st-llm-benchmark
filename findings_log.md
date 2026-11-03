# Findings Log — บันทึกข้อค้นพบเชิงประจักษ์สำหรับบทความ

> ไฟล์สะสมข้อค้นพบระหว่าง pilot/รันจริง พร้อมระบุว่าจะไปปรากฏในส่วนไหนของบทความ (ตามงบ 8 หน้า: RQ1–RQ4, Method, Discussion, Threats to Validity) · ข้อมูลดิบอยู่ใน `pilot_results.jsonl` / `benchmark_results.jsonl` · ห้ามลบรายการ แก้ไขได้เฉพาะเมื่อพิสูจน์ว่าผิด

---

## F-01 · General-purpose โมเดลรุ่น 2024 ตัวเล็กอ่อนมากบน ST (RQ1, RQ2)
- **วันที่:** 2026-10-30 (pilot batch 1)
- **ข้อมูล:** llama3.1:8b, zero-shot, n=30 → **compile 13.3% (4/30), functional 7% (2/30)**; ผ่าน compile เฉพาะ T01/T03/T08/T20 (โจทย์พื้นฐานไร้ state), ผ่าน functional: T01, T08
- **การตีความ:** ประสิทธิภาพตกลงเร็วมากเมื่อโจทย์มี state/timer/ลำดับ — สอดคล้อง RQ2 (ความสามารถ general ไม่ transfer ไป DSL เฉพาะอุตสาหกรรมอัตโนมัติ)
- **ใช้ใน:** Results RQ1 ตารางหลัก + ย่อหน้าเปิด RQ2
- **เทียบเคียง:** Haag et al. 2025 (CORE-3) รายงานโมเดล ~14B ไม่ fine-tune ผ่าน compile ~7% — ตัวเลขเรา 13% อยู่ในหนึ่งมาตราส่วน สนับสนุนความ valid ของ benchmark

## F-02 · Failure mode เด่น: ลืมเซมิโคลอนหลัง END_IF/END_FOR (RQ4)
- **วันที่:** 2026-10-30 (batch 1)
- **ข้อมูล:** Syntax_Grammar_Error 25/26 ที่ fail ของ llama3.1:8b — ตรวจสายตาชุดตัวอย่างพบรูปแบบซ้ำ: `END_IF` ขาด `;` (เช่น T02 บรรทัดที่ 16) ขณะที่โครงสร้าง FUNCTION_BLOCK/VAR ถูกตลอด
- **การตีความ:** โมเดลรู้ "หน้าตา" ของ ST แต่ไม่มี discipline เรื่อง statement terminator — น่าจะเกิดจาก ST ใน pretraining มีสัดส่วนต่ำและปนกับ Pascal/SCL
- **ใช้ใน:** Results RQ4 taxonomy (หมวด Syntax: Missing_Semicolon เป็น sub-category ที่ต้องนับแยก), Discussion

## F-03 · Dialect contamination: คำสั่ง `BEGIN` จากสำเนียงอื่น (RQ4)
- **วันที่:** 2026-10-30 (batch 0)
- **ข้อมูล:** gpt-oss:20b สร้าง T01 ถูกตรรกะ 100% แต่ใส่ `BEGIN` เปิด body (รูปแบบ Pascal/SCL-style) → MatIEC ปฏิเสธ ("invalid variable before ':='")
- **การตีความ:** โมเดลใหญ่รู้จักโครงสร้างแต่ปนภาษาถิ่น — ไม่ใช่ความผิดของ logic เลย → สนับสนุนแนวคิดของงานว่า การตรวจด้วย compiler มาตรฐานเปิดโปงปัญหาที่ BLEU/LLM-judge มองไม่เห็น (โค้ดนี้ "หน้าตา" ใกล้เคียง ground truth มาก)
- **ใช้ใน:** Results RQ4 + Discussion (เทียบกับ LLM-PLC-AS ที่ไม่มี compiler gate), Intro ก็ดึงมาเป็นแรงบันดาลใจได้

## F-04 · คุณภาพข้อมูล: ไม่มีอาร์ติแฟกต์จาก token cap (Threats to Validity)
- **วันที่:** 2026-10-30
- **ข้อมูล:** ตรวจ 30 trials ของ llama3.1:8b — โดนตัดที่ num_predict=800: **0 กรณี** (ใช้จริง 58–127 tokens), ขาด END_FUNCTION_BLOCK: 0 กรณี → failure ทั้งหมดเป็นของโมเดลจริง ไม่ใช่การตัดของเรา
- **ใช้ใน:** Threats to Validity (ข้อโต้แย้ง "โค้ด fail เพราะโดนตัด" — ตัดทิ้งได้ด้วยข้อมูลนี้)
- **หมายเหตุ:** ต้องเช็คซ้ำกับโมเดลช้า/verbose (Qwen3.8-27B, few-shot/CoT) ในรอบ pilot ถัดไป

## F-05 · ปิด thinking mode ผ่าน Ollama API ได้จริง (Method)
- **วันที่:** 2026-10-30
- **ข้อมูล:** `"think": false` ทำงานกับ gpt-oss:20b บน Ollama 0.40.6 (latency 18s, 257 tokens แทนการคิดยาว ๆ) — กลไก fallback กรณี server ไม่รับพารามิเตอร์ก็มีแล้วใน lab script
- **ใช้ใน:** Method (เงื่อนไขการทดลอง — ควบคุม thinking ข้ามโมเดลเพื่อเทียบข้ามตระกูลได้)

## F-06 · กระบวนการ QC ของ benchmark (Method — benchmark contribution)
- **วันที่:** 2026-10-19/30
- **ข้อมูล:** ชุดโจทย์ต้นฉบับ (26 ข้อที่มี) มี ground truth คอมไพล์ไม่ผ่านถึง **9 ข้อ (35%)** — 7 จาก escape ของ Google Docs, 1 ใช้คำสงวน (`Step`), 1 ผิดมาตรฐาน ANY_BIT (SHR กับ INT) · พบเพิ่มจากการ probe: `Integral`/`Derivative` ทำให้ **MatIEC crash** (rc=139) — ข้อจำกัดของเครื่องมือที่ควรบันทึก · ทั้งหมดแก้และผ่านการตรวจ 3 ชั้น (MatIEC + schema + scan-cycle 30/30)
- **การตีความ:** ย้ำว่า dataset ที่ไม่ผ่าน compiler-gate เองจะวัดอะไรผิด ๆ ไปหมด — เสริมเหตุผลที่งานนี้เลือก validation แบบ compiler-based
- **ใช้ใน:** Method §benchmark + repo README; คำเตือนเรื่องคำสงวนใน Discussion ได้

---

## แม่แบบรายการใหม่ (ทำซ้ำต่อ batch)
```
## F-XX · <หัวข้อสั้น> (RQ/ส่วนของบทความ)
- วันที่ / batch:
- ข้อมูล: <ตัวเลข + n>
- การตีความ:
- ใช้ใน: <ส่วน>
```

## F-07 · ⭐ Code-specialist พังเพราะภาษาถิ่น OO: `METHOD ... END_METHOD` (RQ2, RQ4, Threats)
- **วันที่:** 2026-10-30 (pilot batch 2)
- **ข้อมูล:** qwen2.5-coder:14b zero-shot n=30 → **compile 3.3% (1/30 — T13), functional 3.3%** แย่กว่า llama3.1:8b (13%/7%) · สาเหตุหลัก 29/30: ห่อ body ด้วย `METHOD ... BEGIN ... END_METHOD` — ส่วนขยาย OO ของ IEC 61131-3 **ฉบับ 3 (§5.5)** ที่ MatIEC (implement ฉบับ 2 ตาม README ของโปรเจกต์) ไม่รองรับ · โค้ดภายใน METHOD ถูกตรรกะเกือบทั้งหมด (เช่น T01/T08 เห็น assignment ถูกครบ) · ไม่มี truncation (0/30 โดนแคป)
- **การตีความ:** ความเชี่ยวชาญโค้ดสมัยใหม่ = pretrain บนโปรเจกต์ CODESYS/TIA ใหม่ ๆ ที่ใช้ OO-ST → specialist "แปลภาษาถิ่น" แทนที่จะเขียน ST มาตรฐานที่ runtime โอเพนซอร์ส (OpenPLC/Beremiz/MatIEC) กิน · ตอบ RQ2 ตรงข้อความ: specialization ไม่ transfer ไปโปรไฟล์ deployment เป้าหมาย แถมโทษฝั่ง specialist ยิ่งกว่า general
- **การจัดกรอบที่ต้องระวัง (สำคัญ):** METHOD ถูกต้องตามฉบับ 3 — เราวัดเทียบ "ST ที่คอมไพล์กับ MatIEC (2nd edition/OpenPLC profile)" ต้องเขียนชัดใน Method และ Threats to Validity ว่าเกณฑ์คือ deployability บน toolchain โอเพนซอร์ส ไม่ใช่ "ผิดมาตรฐาน" ตรง ๆ
- **optional ablation ไว้ท้ายบทความ/appendix repo:** เพิ่มบรรทัด "plain ST only, no METHODS/OO extensions" ให้ qwen2.5-coder × 5 โจทย์ — ถ้า pass rate กระโดด = ยืนยัน cause เป็น dialect ไม่ใช่ความสามารถ
- **ใช้ใน:** Results RQ2 (หัวใจข้อความ) + RQ4 taxonomy (หมวดใหม่: OO-Dialect_Construct) + Discussion

## F-08 · ⭐ กับดักเชิงเครื่องมือ 2 ชั้นที่ทำให้ค่าวัดเพี้ยนมหาศาล (Method + Threats — บทเรียน QC)
- **วันที่:** 2026-10-30/31 (pilot batch 3 รอบแรก)
- **ข้อมูล:** ผล batch 3 แรกของ gemma4:12b = compile **90%** (27/30) — ตรวจสอบแล้วเป็นของปลอมทั้งหมด มาจากบั๊ก 2 ชั้น: (1) **gemma4:12b เป็น thinking model** ตามพฤติกรรมจริงบน Ollama 0.40.6 (eval=675 tokens แต่ response สุดท้ายยาวแค่ 158 chars — ส่วนคิดกินโควตา num_predict=800 จนบาง run โค้ดขาด/ว่าง) (2) **MatIEC ยอมรับ translation unit ว่างเป็นการคอมไพล์สำเร็จ** (rc=0) → ไฟล์เปล่า = ผ่าน compile ปลอม
- **การแก้:** roster แก้ gemma4 เป็น think-control ✓ (ทดสอบแล้วรับ `"think": false`, eval เหลือ 173) · เพิ่ม guard `Empty_Response` ก่อนเรียกคอมไพล์ · เก็บ `raw_response_head` ทุก trial เพื่อนิรวัติย้อนหลัง · ลบข้อมูล gemma 30 แถวที่เสียและรันใหม่
- **การตีความ (สำคัญต่อวงการ):** (a) การประเมินแบบ compile-only ที่ไม่เช็ค non-empty เพี้ยนได้ถึง 90%→จริง — เสริมเหตุผลทำไมต้องมี Level-2 + QC หลายชั้น (b) `num_predict` ของ Ollamaครอบคลุมทั้ง thinking+answer → โมเดลที่ปิด thinking ไม่ได้จะเสียเปรียบเชิงวิธี ต้องระบุใน Method
- **ใช้ใน:** Method (รายละเอียดเชิงเครื่องมือที่งานอื่นมักไม่เล่า) + Threats to Validity + เป็นเหตุผลออกแบบ fail-hard pipeline

## F-09 · gemma4:12b (general 2026) = ผู้นำ pilot หลังแก้ think/empty: 23%/20% + ตรรกะแน่นเมื่อ syntax ผ่าน (RQ1, RQ2)
- **วันที่:** 2026-10-31 (pilot batch 3 rerun)
- **ข้อมูล:** gemma4:12b zero-shot n=30 → **compile 23.3% (7/30), functional 20% (6/30)** · QC: Empty_Response=0, think_disabled=30/30, truncation=1 · ผ่าน compile: T01/T03/T06/T22/T23/T27/T30 → ผ่าน functional 6/7 (86%) · error: Syntax 17, Block_Closure 6
- **การตีความ:** โปรไฟล์ "syntax-limited, logic-solid" ตรงข้าม llama (ผ่าน syntax บ้างแต่ logic พัง 7%→13% conversion ต่ำกว่า) → อีกหลักฐานว่า compile และ functional เป็นมิติแยกกันจริง (หัวใจที่ต้องวัด 2 ชั้น)
- **ใช้ใน:** Results RQ1 ตาราง + RQ2 (เทียบ conversion rate compile→functional ข้ามโมเดล — เมตริกใหม่ที่เรานิยาม)

## F-10 · ⭐⭐ ยืนยันเด็ดขาด: few-shot ตัวอย่าง plain-ST เปลี่ยนภาษาถิ่นของ coder model ได้ทั้งหมด (RQ2 + ปฏิสัมพันธ์โมเดล×กลยุทธ์)
- **วันที่:** 2026-10-31 (pilot batch 4a/4b)
- **ข้อมูล:** qwen2.5-coder:14b — zero-shot 3%/3% (METHOD 29/30) → **few-shot 43%/20% (METHOD 0/30)** · ส่วน llama3.1:8b ตอบสนองน้อยมาก: zero 13%/7% → few-shot 17%/7% → CoT 17%/7%
- **การตีความ:** (1) สมมติฐาน F-07 ยืนยันเต็ม: ความสามารถมีอยู่ ปัญหาคือ dialect selection (2) ผลของ prompting **ขึ้นกับตระกูลโมเดยักษ์** — few-shot ทำหน้าที่เป็น "dialect anchor" สำหรับ coder แต่แทบไม่ช่วย general ที่มีปัญหา syntax พื้นฐาน (3) นี่คือ interaction โมเดล×กลยุทธ์ที่ two-way ANOVA ใน PROTOCOL §3 ตั้งใจจับพอดี — คาดว่าในรันเต็มจะ significant
- **นัยต่อการนำไปใช้ (Discussion):** วิศวกรใช้โมเดล coder local กับ ST ต้องมีตัวอย่าง dialect ประกอบเสมอ — คำแนะนำปฏิบัติที่ตรงจุดจากข้อมูล
- **ใช้ใน:** Results RQ2 (headline) + ปฏิสัมพันธ์ใน ANOVA + Discussion (practical guidance)

## F-11 · qwen3-coder:30b รันบน M5/32GB ได้จริง แต่ช้าเกินสำหรับรันเต็ม — ยืนยันแผน hybrid GCP (RQ3/infra)
- **วันที่:** 2026-10-31 (pilot batch 5 load test)
- **ข้อมูล:** โหลด+รันผ่าน 5/5 trials ไม่มี OOM/stall · แต่ latency **188–656 วินาที/trial** (MoE 19GB บน 32GB unified — น่าจะโดนขอบ wired memory) → ประมาณ 450 trials ของโมเดลนี้ ≈ 45–75 ชม. บนเครื่อง · ผลคุณภาพ: T01 ผ่านทั้ง compile+functional (Tier-A ตัวแรกทะลุ), แต่ zero-shot 4/5 fail compile — สอดคล้องพฤติกรรมภาษาถิ่นของตระกูล Qwen-coder (F-07/F-10)
- **การตีความ:** (1) สถาปัตยกรรม hybrid ในแผนถูกต้อง — โมเดลใหญ่รันบน GCP L4, เครื่อง M5 เก็บ latency case study (2) tok/s=None ใน log = Ollama ไม่ส่ง eval_duration สำหรับโมเดลนี้ — ต้องเก็บเมตริกจาก eval_count×ล.ม. แทน (แก้ใน lab script ก่อนรันเต็ม)
- **ใช้ใน:** RQ3 (hardware trade-off) + การตัดสินใจ infra ของการทดลองหลัก

## F-12 · ⚠️ think:false บน /api/generate "ถูกรับแต่ไม่มีผล" กับ gpt-oss (Method/QC — ต้องแก้ก่อนรันเต็ม)
- **วันที่:** 2026-11-01 (pilot batch 6)
- **ข้อมูล:** gpt-oss:20b zero-shot n=30 → **Empty_Response 14/30 (47%)** ทุก case มี eval=800 (ชนแคปพอดี), think_disabled=True, raw response ว่าง — เหตุ: gpt-oss คิดใน token stream ต่อเนื่อง และ think:false บน /api/generate (Ollama 0.40.6) ไม่ยับยั้งการคิดของโมเดลนี้ (รับพารามิเตอร์แบบเงียบ ๆ) · โจทย์ง่าย (T01) ผ่านเพราะคิดสั้น — smoke test ครั้งแรกเลยไม่เผย
- **ผลกระทบถ้าไม่แก้:** เทียบข้ามโมเดลจะอยุ่ย gpt-oss ครึ่งหนึ่งของข้อมูลหายเป็น empty
- **แผนแก้:** ทดสอบ `/api/chat` + think:false (endpoint หลักของ Ollama) → ถ้าได้ผลสลับ client ทั้งหมดไป chat endpoint (ใช้ system message แทน prefix) แล้วรัน gpt-oss ซ้ำ · ต้องทำหลังคิว pilot ปัจจุบันจบ เพื่อไม่ให้ model swapping เพี้ยน latency ของ deepseek
- **ใช้ใน:** Method (รายละเอียด think-control ต่อโมเดล/endpoint) + Threats

## F-13 · ภาพรวม pilot ครบ 8 โมเดล + 2 ข้อสังเกตความผิดปกติ (RQ1 ฐานเต็ม + QC)
- **วันที่:** 2026-11-01 (pilot ครบ 8/8, 288 trials)
- **ข้อมูล (zero-shot):** qwen3.5:27b นำ 33%/23% · gemma4 23%/20% · qwen2.5-coder 3%→(few-shot 43%) · llama 13%/7% · qwen3-coder 20%/20% (n=5 โหลดเทส) · gpt-oss 10%/7% (⚠️ 47% empty รอแก้ F-12) · **deepseek 0%/0%** (METHOD ภาษาถิ่น 28/30 — โรคประจำตระกูล coder รุนแรงกว่า qwen) · **qwen3.8 0%/0%**
- **นิรวัติ qwen3.8:** output สั้นผิดปกติ (eval~80 tok) — มี `//` comment 16/30 (ถูกฉบับ 3 แต่ MatIEC ฉบับ 2 ปฏิเสธ) และ/หรือ **ลืม END_FUNCTION_BLOCK** · sensitivity หลังการทดลอง (strip // แล้วคอมไพล์ใหม่): **rescue เพียง 2/258 trials ทั้ง dataset** → ปัญหาหลักคือโครงสร้างไม่จบ ไม่ใช่ comment → ใช้ strict compile ต่อ + รายงาน sensitivity นี้ใน Threats to Validity
- **นิรวัติ deepseek:** ช้าผิดปกติบน M5 (เฉลี่ย 322 วิ/trial, ~0.8 tok/s — ช้ากว่า dense 14B สิบเท่า น่าจะ memory thrash บน unified 32GB) + ป่วย METHOD เหมือน qwen-coder → ยืนยันอีกครั้งว่าโค้ดเดอร์ตระกูล 2024 ทั้งสาย overfit ภาษาถิ่น OO; เร็ว/ถูกแค่บน GCP
- **ใช้ใน:** RQ1 ตารางเต็ม + RQ2 (coder vs general กลับหัวใน zero-shot) + Threats (sensitivity + hardware ข้อจำกัด M5)

## F-14 · ⭐ ตาราง pilot สมบูรณ์ 8/8 (zero-shot) — gpt-oss แก้ think แล้วขึ้นนำด้วยความเร็วสูงสุด (RQ1 ฉบับเต็ม)
- **วันที่:** 2026-11-01 (pilot ปิดจ๊อบ, 318 trials ใช้การวิเคราะห์)
- **ข้อมูล:** gpt-oss:20b (think="low") **37%/30% + เร็วสุด 7.7 วิ/trial (34 tok/s) ไม่มี Empty เลย** (จาก 10%/7% ที่พัง 47%) · อันดับ: gpt-oss 37/30 > qwen3.5 33/23 > gemma4 23/20 > qwen3-coder 20/20(n=5) > llama 16/7 > qwen2.5-coder 3/3 (few-shot 43/20) > deepseek 0/0, qwen3.8 0/0
- **การตีความ:** (1) 2025 open-weight (gpt-oss) นำ zero-shot แบบขาด (2) coder ทั้งสองตัว 2024 ก้ำกึ่ง 0% เพราะภาษาถิ่น — ตรงข้ามกับ qwen3-coder 2025 ที่รอดบ้าง (3) โมเดลล้ม "เป็นกลุ่มตามตระกูล+ยุค" ชัดเจน → RQ2/RQ4 มีโครงเรื่องพร้อม · ยืนยันว่า think-control ที่ผิด = ทำให้โมเดลดูแย่กว่าจริงมาก (30%→7%) — ข้อควรระวังสำคัญของงาน benchmark ที่ใช้ Ollama
- **ใช้ใน:** Results RQ1 ตารางหลัก + Method (think-control per-model) + Discussion

## F-15 · ⭐⭐⭐ ผลชุดเต็ม 3,600 trials: อันดับสุดท้าย + นัยสำคัญทางสถิติครบ (RQ1)
- **วันที่:** 2026-11-02 (รัน ~29 ชม. บน L4, ต้นทุนรวมคลาวด์ ~$24, โดน preemption 1 ครั้ง กู้คืนด้วย checkpoint)
- **functional pass@1 / pass@5 (ต่อโจทย์ 5 runs):**
  1. **qwen3.8:27b — 0.49 / 0.64** (few-shot: compile 81% func 59%!) 🏆
  2. gpt-oss:20b — 0.36 / 0.62 (few-shot 60/45) + เร็วสุด 4–5 วิ/trial
  3. qwen3-coder:30b — 0.26 / 0.39 | gemma4:12b — 0.23 / 0.42 | qwen3.5:27b — 0.22 / 0.43
  5. qwen2.5-coder:14b 0.10 | llama3.1:8b 0.07 | deepseek 0.03
- **สถิติ:** Friedman ทุกกลยุทธ์ p≈1e-14 · Wilcoxon+Bonferroni: qwen3.8 เหนือ deepseek/llama/qwen2.5-coder/qwen3.5/gemma4 (★), gpt-oss เหนือ qwen2.5-coder/llama/deepseek (★), δ ระดับ -0.29..-0.54
- **ใช้ใน:** Results ตารางหลัก + pass@k รูปที่ 1

## F-16 · ⭐⭐⭐ ปฏิสัมพันธ์โมเดล×กลยุทธ์ระดับมหาศาล (RQ2)
- few-shot (dialect anchor): qwen2.5-coder compile 5%→41%, deepseek 0%→11%, qwen3.8 55%→81% — ยืนยัน F-10 ในสเกลเต็ม
- **CoT ทำร้ายหลายตัว:** qwen3-coder compile 43%→16%, gemma4 27%→13% (ขณะที่ gpt-oss ได้ประโยชน์ 35→45) — ไม่ใช่ truncation (trunc 0%) ต้องวิเคราะห์ต่อใน RQ4
- **ใช้ใน:** Results RQ2 + two-way ANOVA (อยู่ใน stats_summary.json)

## F-17 · ⚠️ ความต่างของสภาพแวดล้อม Ollama เปลี่ยนผลรุนแรง (Threats to Validity — ต้องจัดการตอนเขียน)
- qwen3.8:27b บน M5/Ollama 0.40.6 (pilot) = **0%** compile (โครงสร้างไม่จบ) แต่บน VM/Ollama ล่าสุดปี 2026-11-01 = **55–81%** — คาดว่าคนละเวอร์ชันจัดการ think/truncation ต่างกัน · ผลหลักทั้งหมดมาจาก VM เครื่องเดียว (สภาพแวดล้อมเดียว สม่ำเสมอ ✓) แต่ต้อง (1) บันทึกเวอร์ชัน Ollama ให้ชัด (2) อธิบายความต่าง pilot-vs-full (3) gemma4/qwen3.5 มี truncation สูง 55–71% บน VM → บทวิเคราะห์ budget-exhaustion ต้องรายงาน
- **บทเรียน:** ต้องเก็บ `ollama --version` ของ VM ตอนจบรัน (ลืม — เครื่องถูกลบแล้ว) → ระบุ "latest stable @ 2026-11-01" และเพิ่มขั้นตอนนี้ใน checklist การทดลองอนาคต
- **ใช้ใน:** Threats to Validity (environment consistency) + Method (version pinning)

## F-18 · ⭐⭐⭐ RQ4 ฉบับเต็ม: Failure taxonomy = "ลายนิ้วมือภาษาถิ่น" ของแต่ละตระกูลโมเดล (RQ4 — หัวใจของส่วนนี้)
- **วันที่:** 2026-11-02 (taxonomy.json, 3,600 trials: PASS 1,052 / FAIL 2,548)
- **ตารางหลัก (โมเดล×สาเหตุหลัก):**
  - **Empty_Response 553** — gemma4 (248) + qwen3.5 (294): โรค "คิดกินโควตา" แย่ลงตามลำดับ zero→few→cot (gemma 75/83/90)
  - **Dialect_OO_METHOD 505** — deepseek (246) + qwen2.5-coder (259): โรคประจำ coder ยุค 2024 (F-07 ในสเกลเต็ม)
  - **C_Style_Comment 431** — qwen3-coder (246!), qwen3.8 (67), qwen2.5-coder (58): ใช้ `//` (ฉบับ 3) กับคอมไพเลอร์ฉบับ 2
  - **Missing_Semicolon 521** — llama (312!), gpt-oss (120): ลายเซ็นความหละหลวม
  - **Missing_END_FUNCTION_BLOCK 197** — deepseek (78), gemma4 (58)
  - รอย: Dialect_SCL_BEGIN 91 (deepseek ป่วยสองโรคพร้อมกัน!), Type 24 ฯลฯ
- **การตีความ (แนวคิดเด่นของบทควาท):** รูปแบบความล้มของแต่ละตระกูล = **"dialect fingerprint"** สะท้อนว่า pretraining corpus ของโมเดลนั้นดูด ST มาจากคนละยุค/คนละเจ้า (CODESYS ใหม่ vs ตำราคลาสสิก vs Pascal) — อธิบายทั้ง RQ2 (specialist ไม่จำเป็นได้เปรียบ) และความสำคัญของ compiler-gate
- **ใช้ใน:** Results RQ4 ตาราง + Discussion (แนวคิด fingerprint) — นี่คือตารางเดียวที่ "เล่าเรื่องได้ทั้งบท"

## F-19 · ปริศนา CoT-degradation แกะออกแล้ว: CoT ชวนให้เขียน "โค้ดมีคอมเมนต์" (RQ2/RQ4)
- **ข้อมูล:** qwen3-coder compile ตก 43%→16% เมื่อใช้ CoT — สาเหตุจาก taxonomy: C_Style_Comment คือหมวดใหญ่สุดของโมเดลนี้ (246) และตัวอย่างจริงยืนยัน: CoT prompt → โมเดลเขียนโค้ดพร้อม `// Initialize timer whe...` คลุมทุกฟังก์ชัน · gemma4 ตกเพราะ Empty เพิ่ม (คิดยาวขึ้น) 75→90
- **การตีความ:** ผลข้างเคียง CoT สองทาง: (1) ชวนใส่คอมเมนต์เอกสาร (ซึ่งฟอร์แมตฉบับ 3 = ตายกับ compiler ฉบับ 2) (2) กระตุ้น reasoning ที่กิน budget · ส่วน gpt-oss ได้ประโยชน์จาก CoT เพราะคุม reasoning ได้ (think=low)
- **ใช้ใน:** Results RQ2 (ปฏิสัมพันธ์) + Discussion (คำแนะนำ: few-shot > CoT สำหรับ ST deployment)
