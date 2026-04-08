#!/bin/bash
# Auto-connect to ELM327 Bluetooth OBD-II adapter 
# on boot
MAC="01:23:45:67:89:BA" PIN="1234" echo "[INFO] 
Initializing Bluetooth connection for ELM327 
($MAC)..."
# Ensure Bluetooth service is up
sudo systemctl start bluetooth
# Pair and trust the adapter if not already stored
bluetoothctl << EOF agent on default-agent remove 
$MAC pair $MAC trust $MAC connect $MAC quit EOF
# Bind to serial device /dev/rfcomm0
sudo rfcomm release 0 >/dev/null 2>&1 sudo rfcomm 
bind 0 $MAC
# Give a short pause to ensure rfcomm0 is ready
sleep 2
# Verify connection
if [ -e /dev/rfcomm0 ]; then echo "[OK] ELM327 
  connected and bound to /dev/rfcomm0"
else echo "[ERROR] Failed to bind ELM327. Check 
  Bluetooth pairing." exit 1
fi
# Start the AI Dashboard
echo "[INFO] Launching Subaru AI Dashboard..." cd 
/home/pi/subaru/ssm python3 ssm_ai_dash_elm327.py
