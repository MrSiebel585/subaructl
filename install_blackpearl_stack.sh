#!/bin/bash

set -e

BASE="/opt/subaru"
BIN="$BASE/bin"
LOGDIR="$BASE/logging"

echo "[*] Installing Black Pearl ECU Control Stack..."

# Create directories
sudo mkdir -p $BIN
sudo mkdir -p $LOGDIR

# -----------------------------
# Device Detection Script
# -----------------------------
sudo tee $BIN/bp-detect-device.sh > /dev/null <<'EOF'
#!/bin/bash

if lsusb | grep -qi "FTDI"; then
    echo "TACTRIX"
    exit 0
fi

if ls /dev/rfcomm* 1>/dev/null 2>&1; then
    echo "ELM327_BT"
    exit 0
fi

if ls /dev/ttyUSB* 1>/dev/null 2>&1; then
    echo "USB_SERIAL"
    exit 0
fi

echo "NONE"
exit 1
EOF

# -----------------------------
# Session Creator
# -----------------------------
sudo tee $BIN/bp-session.sh > /dev/null <<'EOF'
#!/bin/bash
BASE="/opt/subaru/logging"
SESSION="$BASE/session_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SESSION"
echo "$SESSION"
EOF

# -----------------------------
# Intelligent Logger Router
# -----------------------------
sudo tee $BIN/bp-log.sh > /dev/null <<'EOF'
#!/bin/bash

DEVICE=$(/opt/subaru/bin/bp-detect-device.sh)
SESSION=$(/opt/subaru/bin/bp-session.sh)

echo "[*] Device: $DEVICE"
echo "[*] Session: $SESSION"

case "$DEVICE" in
  TACTRIX)
    echo "[*] Using SSM stack"
    /opt/subaru/ssm2csv_run.sh > "$SESSION/raw_log.csv"
    ;;
  ELM327_BT)
    echo "[*] Using Bluetooth OBD stack"
    python3 /opt/subaru/obd2_realtime_monitor.py > "$SESSION/raw_log.csv"
    ;;
  USB_SERIAL)
    echo "[*] Using USB OBD logger"
    python3 /opt/subaru/diagnostics_logger.py > "$SESSION/raw_log.csv"
    ;;
  *)
    echo "[!] No supported OBD device found."
    exit 1
    ;;
esac

echo "[*] Log saved to $SESSION/raw_log.csv"
echo "$SESSION"
EOF

# -----------------------------
# ROM Tagging
# -----------------------------
sudo tee $BIN/bp-tag-rom.sh > /dev/null <<'EOF'
#!/bin/bash

ROM="$1"
SESSION="$2"

if [ -z "$ROM" ] || [ -z "$SESSION" ]; then
    echo "Usage: bp-tag-rom.sh rom.bin session_dir"
    exit 1
fi

cp "$ROM" "$SESSION/"
sha256sum "$ROM" > "$SESSION/rom.sha256"

echo "[*] ROM fingerprinted."
EOF

# -----------------------------
# AI Log Analysis
# -----------------------------
sudo tee $BIN/bp-analyze.sh > /dev/null <<'EOF'
#!/bin/bash

SESSION="$1"
MODEL="blackpearl-stage1_5"

if [ -z "$SESSION" ]; then
    echo "Usage: bp-analyze.sh /path/to/session"
    exit 1
fi

LOG="$SESSION/raw_log.csv"
OUT="$SESSION/ai_analysis.md"

PROMPT="Analyze this Subaru WRX log for:
- Injector duty margin
- Boost stability
- Knock trend
- Thermal stability
- Ringland or bearing stress risk.
Provide engineering-level commentary."

echo "$PROMPT" > /tmp/bp_prompt.txt
cat "$LOG" >> /tmp/bp_prompt.txt

ollama run $MODEL < /tmp/bp_prompt.txt > "$OUT"

rm /tmp/bp_prompt.txt

echo "[*] AI analysis saved to $OUT"
EOF

# -----------------------------
# Master Control Command
# -----------------------------
sudo tee $BASE/blackpearlctl > /dev/null <<'EOF'
#!/bin/bash

case "$1" in
  detect)
    /opt/subaru/bin/bp-detect-device.sh
    ;;
  log)
    /opt/subaru/bin/bp-log.sh
    ;;
  analyze)
    /opt/subaru/bin/bp-analyze.sh "$2"
    ;;
  full-run)
    SESSION=$(/opt/subaru/bin/bp-log.sh)
    /opt/subaru/bin/bp-analyze.sh "$SESSION"
    ;;
  *)
    echo "Black Pearl ECU Control"
    echo "Usage:"
    echo "  blackpearlctl detect"
    echo "  blackpearlctl log"
    echo "  blackpearlctl analyze /path/to/session"
    echo "  blackpearlctl full-run"
    ;;
esac
EOF

# Make everything executable
sudo chmod +x $BIN/bp-*.sh
sudo chmod +x $BASE/blackpearlctl

# Optional: Add to PATH
if ! grep -q "/opt/subaru" ~/.bashrc; then
    echo 'export PATH=$PATH:/opt/subaru' >> ~/.bashrc
    echo "[*] Added /opt/subaru to PATH (restart shell or run: source ~/.bashrc)"
fi

echo "[✓] Black Pearl Control Stack Installed Successfully."
echo "Run: blackpearlctl detect"
