# Subaru Operator Runbook

This runbook defines the primary operating flows and first-response recovery actions.

## 1) Live SSM Logging (`/dev/ttyACM0`)

Prereqs:
- Tactrix/OpenPort connected
- `pyserial` installed

Commands:
```bash
cd /home/jeremy/subaru
python3 -m pip install pyserial
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
SUBARU_SSM_PORT=/dev/ttyACM0 SUBARU_SSM_BAUD=9600 python3 logging/ssm_logger_csv.py
```

Expected:
- `Connected to /dev/ttyACM0 @ 9600 baud`
- Repeating `Logged <n> parameters`

Stop:
- `Ctrl+C`

## 2) Live ELM Dashboard (`/dev/rfcomm0`)

Prereqs:
- ELM327 paired and bound as `/dev/rfcomm0`
- Dashboard deps installed

Commands:
```bash
cd /home/jeremy/subaru
python3 -m pip install -r wrxdash/requirements.txt
ls /dev/rfcomm0
SUBARU_ELM327_PORT=/dev/rfcomm0 python3 wrxdash/app.py
```

Open:
- `http://localhost:8080`

Expected:
- Flask/SocketIO startup logs
- live OBD updates in dashboard

## 3) ROM Extract -> Diff -> Safety Audit

Prereqs:
- ROM binaries and XML defs available

Commands:
```bash
cd /home/jeremy/subaru/ecu_extractor
python3 cli.py /path/to/stock.bin --defs /home/jeremy/subaru/definitions/ecu_defs.xml --out stock.json
python3 cli.py /path/to/tuned.bin --defs /home/jeremy/subaru/definitions/ecu_defs.xml --out tuned.json
python3 diff_cli.py stock.json tuned.json --out diff_output.json
python3 safety_cli.py /path/to/rom_directory --out safety_audit.json
```

Outputs:
- `stock.json`
- `tuned.json`
- `diff_output.json`
- `safety_audit.json`

## 4) Log Replay for `wrxdash` Analysis

1. Start dashboard:
```bash
cd /home/jeremy/subaru
SUBARU_ELM327_PORT=/dev/rfcomm0 python3 wrxdash/app.py
```

2. Open:
- `http://localhost:8080`
- Use Logs/Replay controls in UI

3. API checks (optional):
```bash
curl -s http://localhost:8080/api/logs
curl -s http://localhost:8080/api/logs/<filename>/stats
```

Expected:
- replay emits `obd_update` events
- stats endpoint returns row/count metadata

## 5) Failure Recovery Playbook

### A) Device missing

Symptoms:
- `No such file or directory: /dev/ttyACM0` or `/dev/rfcomm0`

Actions:
```bash
ls /dev/ttyACM* /dev/ttyUSB* /dev/rfcomm* 2>/dev/null
ls /dev/serial/by-id/ 2>/dev/null
```
- Re-seat cable / power-cycle adapter
- Update env var to actual path:
  - `SUBARU_SSM_PORT=/dev/ttyUSB0`
  - `SUBARU_ELM327_PORT=/dev/rfcomm1`

### B) Serial busy / permission denied

Symptoms:
- `Permission denied`
- `Device or resource busy`

Actions:
```bash
groups
sudo usermod -aG dialout "$USER"
lsof /dev/ttyACM0
lsof /dev/rfcomm0
```
- Stop conflicting process using the port
- Re-login after group change

### C) No ECU response

Symptoms:
- Connects to serial, but no valid frames / no telemetry

Actions:
- Verify ignition state (ON)
- Try alternate baud:
```bash
SUBARU_SSM_BAUD=4800 SUBARU_SSM_PORT=/dev/ttyACM0 python3 logging/ssm_logger_csv.py
```
- For ELM327, reinitialize adapter and re-pair Bluetooth
- Confirm adapter compatibility for Subaru protocol path being used

### D) Dashboard up but no live data

Actions:
- Confirm source logger/device is active
- Check server logs for reader init errors
- Verify API:
```bash
curl -s http://localhost:8080/api/logs
```

### E) Fast rollback

Use known-good commands:
```bash
cd /home/jeremy/subaru
./run_all_help.sh list
./run_all_help.sh run 21   # SSM CSV logger
./run_all_help.sh run 2    # wrxdash app
```
