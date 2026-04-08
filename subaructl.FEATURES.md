# New subaructl Features Recommendations

1. **Live Monitor** (`subaructl monitor`)
   ```
   watch -n1 'subaructl doctor --json | jq'
   ```
   - Real-time diagnostics dashboard.

2. **Auto-Fix** (`subaructl fix`)
   - pip install missing modules.
   - sudo usermod dialout.

3. **Device Scan** (`subaructl scan`)
   ```
   lsusb | rg ELM327
   bluetoothctl scan on
   ```
   - Auto-set SUBARU_* ports.

4. **JSON API** (`subaructl doctor --json`)
   - jq/machine-parse diagnostics.

5. **Workflows** (`subaructl workflow tune`)
   - doctor → patch → ssm-log → monitor.

**Priority**: JSON > Scan > Auto-fix.

Implement top 3?
