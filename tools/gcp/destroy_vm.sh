#!/bin/bash
# ลบ VM + disk ทิ้ง = หยุดค่าใช้จ่ายทั้งหมด (ผลการทดลองอยู่ใน .jsonl ที่ดาวน์โหลดกลับแล้วเท่านั้น!)
# ตรวจก่อนลบ: ดาวน์โหลด benchmark_results.jsonl กลับมาก่อนเสมอ
set -euo pipefail
PROJECT=iec-st-llm-bench
ZONE=us-central1-a
VM=iec-st-bench-runner

echo "── ดาวน์โหลดผลลัพธ์ล่าสุดกลับเครื่อง (ถ้ามี) ──"
gcloud compute scp --project=$PROJECT --zone=$ZONE \
  "$VM:~/bench/benchmark_results.jsonl" ./vm_benchmark_results.jsonl 2>/dev/null \
  && echo "ดาวน์โหลดแล้ว → ./vm_benchmark_results.jsonl" \
  || echo "(ยังไม่มีไฟล์ผลบน VM หรือ ssh ไม่ได้ — ถ้ามีผลสำคัญอยู่บนนั้นอย่าข้ามขั้นนี้!)"

read -rp "ยืนยันลบ $VM ใน $PROJECT/$ZONE? [y/N] " ans
[ "$ans" = "y" ] || exit 1
gcloud compute instances delete "$VM" --project="$PROJECT" --zone="$ZONE" --quiet
echo "✓ ลบแล้ว — ไม่มีค่าใช้จ่ายต่อเนื่องคงเหลือ (นอกจาก disk อื่นที่สร้างเอง)"
gcloud compute disks list --project="$PROJECT" --format="table(name,sizeGb,status)"
