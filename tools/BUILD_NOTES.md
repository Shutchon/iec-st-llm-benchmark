# MatIEC (iec2c) Build Notes

**ตำแหน่งถาวร:** `tools/matiec/` (อย่า build ใน /tmp — macOS ลบไฟล์ /tmp ที่ไม่ได้แตะ 3 วัน ทำเสีย build ไปแล้วครั้งหนึ่ง)
**ตรวจสอบล่าสุด:** 2026-10-19 บน macOS ARM64 (M5) — build ผ่าน, ใช้งานได้

## macOS (ARM64)
```bash
brew install autoconf automake libtool bison     # bison ของ Apple (2.3) เก่าเกินไป
export PATH=/opt/homebrew/opt/bison/bin:/opt/homebrew/bin:$PATH
cd tools/matiec
autoreconf -i && ./configure && make -j8
```

## Linux x86_64 (สำหรับ VM บน GCP)
```bash
sudo apt update && sudo apt install -y build-essential autoconf automake bison flex git
git clone --depth 1 https://github.com/beremiz/matiec.git && cd matiec
autoreconf -i && ./configure && make -j"$(nproc)"
```

## การเรียกใช้ (สำคัญ)
ต้องชี้ standard library ด้วย `-I` เสมอ ไม่งั้น error "ieclib.txt not found":
```bash
tools/matiec/iec2c -I tools/matiec/lib <file.st>    # ผ่าน = exit 0, ผิด = exit 1 + error ระบุบรรทัด
```

## เวอร์ชันที่ใช้
- git HEAD ณ 2026-10-18 (clone --depth 1) — บันทึก commit hash จริงตอน lock เวอร์ชันเพื่อใส่ในบทความ:
  `cd tools/matiec && git rev-parse HEAD`
