#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# provision บน VM (รันอัตโนมัติผ่าน startup-script ตอนบูตเครื่อง)
# ติดตั้ง: NVIDIA driver → Ollama → MatIEC → ดึงโมเดล 8 ตัว
# ─────────────────────────────────────────────────────────────────
set -euo pipefail
export HOME=/root   # ollama CLI panic ถ้าไม่มี HOME (startup script รันโดยไม่ตั้ง)
exec > /var/log/provision.log 2>&1
echo "=== provision start $(date) ==="

# 1) NVIDIA driver สำหรับ L4 (Ubuntu 24.04)
if ! nvidia-smi >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y "linux-headers-$(uname -r)" nvidia-utils-570-server nvidia-driver-570-server
  echo "driver ติดตั้งแล้ว ต้อง reboot"; reboot; exit 0
fi
nvidia-smi

# 2) Ollama (ตัวติดตั้ง include CUDA runtime ในตัว)
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
  systemctl enable --now ollama
fi
ollama --version

# 3) MatIEC (build บน Linux x86_64 ตาม tools/BUILD_NOTES.md)
if [ ! -f /opt/matiec/iec2c ]; then
  apt-get install -y build-essential autoconf automake bison flex git
  git clone --depth 1 https://github.com/beremiz/matiec.git /opt/matiec
  cd /opt/matiec && autoreconf -i && ./configure && make -j"$(nproc)"
fi
/opt/matiec/iec2c 2>&1 | head -1 || true

# 4) ดึงโมเดลทั้ง roster 8 ตัว (ตามลำดับเล็ก→ใหญ่ จะได้มีตัวใช้ก่อน)
MODELS="llama3.1:8b gemma4:12b qwen2.5-coder:14b deepseek-coder-v2:16b gpt-oss:20b qwen3.5:27b qwen3.8:27b qwen3-coder:30b"
for m in $MODELS; do
  echo "── pulling $m"
  ollama pull "$m" || echo "!! pull $m ล้มเหลว (ดำเนินการต่อ)"
done

echo "=== provision done $(date) ==="
touch /var/log/provision.DONE
