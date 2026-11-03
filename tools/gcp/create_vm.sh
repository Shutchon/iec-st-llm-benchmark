#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# สร้าง Spot VM g2-standard-8 (1× L4) สำหรับรัน benchmark
# ใช้เมื่อ: โมเดล + harness พร้อมแล้วเท่านั้น (เครื่องรัน = เงินไหล)
# หลัง provision เสร็จ (~15–25 นาที): คัดลอกโค้ดขึ้นไปด้วยคำสั่ง rsync ท้ายสคริปต์
# ─────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
PROJECT=iec-st-llm-bench
ZONE="${ZONE:-us-central1-a}"   # ส่งทับได้: ZONE=us-central1-c bash create_vm.sh
VM=iec-st-bench-runner

gcloud compute instances create "$VM" \
  --project="$PROJECT" --zone="$ZONE" \
  --machine-type=g2-standard-8 \
  --accelerator=count=1,type=nvidia-l4 \
  --provisioning-model=SPOT --instance-termination-action=STOP \
  --boot-disk-size=200GB --boot-disk-type=pd-balanced \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --metadata-from-file=startup-script=vm_provision.sh

echo
echo "▶ รอ provision 15–25 นาที แล้วตรวจด้วย:"
echo "  gcloud compute ssh $VM --project=$PROJECT --zone=$ZONE -- 'tail /var/log/provision.log'"
echo "  gcloud compute ssh $VM --project=$PROJECT --zone=$ZONE -- 'ollama list'"
echo
echo "▶ คัดลอก harness + dataset ขึ้น VM (ตอน provision.DONE แล้ว):"
echo "  gcloud compute scp --recurse --project=$PROJECT --zone=$ZONE \\"
echo "    ../..//plc_llm_benchmark_lab.py ../..//benchmark $VM:~/bench/ 2>/dev/null || {"
echo "    gcloud compute ssh $VM --project=$PROJECT --zone=$ZONE -- 'mkdir -p ~/bench/benchmark';"
echo "    gcloud compute scp --project=$PROJECT --zone=$ZONE ../..//plc_llm_benchmark_lab.py $VM:~/bench/;"
echo "    gcloud compute scp --project=$PROJECT --zone=$ZONE ../..//benchmark/tasks.json $VM:~/bench/benchmark/; }"
echo
echo "▶ หลังใช้เสร็จ — ปิดจุดที่นับเงิน ทันที:"
echo "  bash destroy_vm.sh"
