# Subaru

Note: The SSM logger requires a valid serial device (e.g. `/dev/ttyACM0`) and `pyserial` installed. If the device is missing, the logger will exit with a port error.

Runbook:
- See [OPERATOR_RUNBOOK.md](./OPERATOR_RUNBOOK.md) for live operations, replay flow, ROM workflow, and failure recovery.

Doctor:
- Run `./subaructl doctor` to validate devices, permissions, dependencies, and dashboard API reachability.

## Setup (Manual)

1) Install Python deps:
   - `python3 -m pip install pyserial`

2) Identify your serial device (examples):
   - `ls /dev/ttyACM*`
   - `ls /dev/ttyUSB*`
   - `ls /dev/serial/by-id/`

3) Run the SSM CSV logger:
   - `SUBARU_SSM_PORT=/dev/ttyACM0 SUBARU_SSM_BAUD=9600 python3 logging/ssm_logger_csv.py`

4) Run the OBD dashboard (if using ELM327):
   - `SUBARU_ELM327_PORT=/dev/rfcomm0 python3 wrxdash/app.py`

## Automated Installer (Recommended)

1. Place `install-subaru-stack.sh` in project root
2. `chmod +x install-subaru-stack.sh`
3. `sudo ./install-subaru-stack.sh`
4. Logout/login (PATH)
5. `subaructl --help` | `blackpearlctl detect`

Sets up venvs, builds FastECU, symlinks, services, desktop entry.

## Finishing Code Development Recommendations

The workspace has the main operational pieces in place, but it still needs a short finishing pass to turn it into a more consistent development surface.

1. Standardize the runtime contract.
   - Route serial ports, baud rates, log directories, dashboard host/port, and ROM paths through `subaru_config/`.
   - Remove hard-coded device paths and one-off environment handling from app entrypoints.
   - Prefer `subaructl doctor` as the shared preflight check before starting loggers, dashboards, or ROM tooling.

2. Finish the logging and error-handling cleanup.
   - Replace remaining `print()`-driven status output in `wrxdash/`, `logging/`, and serial tooling with structured logging.
   - Narrow broad exception handlers so serial errors, protocol errors, and unexpected faults are handled differently.
   - Add throttled warnings for disconnected devices and repeated transient failures.

3. Reduce app-level coupling.
   - Split `wrxdash/app.py` responsibilities into route handlers, services, and device/telemetry adapters.
   - Keep protocol-specific reads out of Flask route code.
   - Move reusable serial and ECU logic into testable modules instead of script entrypoints.

4. Close the testing gaps around real workflows.
   - Add route/service integration tests for dashboard APIs and replay flow.
   - Add parser and transformation tests for ROM analysis, telemetry normalization, and log replay.
   - Treat hardware access as an interface and test it with mocks or fixtures instead of requiring a live adapter.

5. Add graceful shutdown and recovery behavior.
   - Ensure long-running readers and background threads stop cleanly on `SIGINT` and `SIGTERM`.
   - Centralize reconnect logic for `/dev/ttyACM*`, `/dev/ttyUSB*`, and `/dev/rfcomm*` devices.
   - Make failure states observable in logs and `subaructl doctor`.

6. Define one supported developer workflow.
   - Document the canonical commands for setup, validation, dashboard start, logging start, replay, and ROM analysis.
   - Keep that workflow at the workspace root so developers do not need to infer which subproject owns each step.
   - Prefer adding small task wrappers to `subaructl` over introducing more standalone scripts.

Recommended finish order:
- Logging/error cleanup
- `wrxdash` separation and shutdown handling
- Integration tests for dashboard and replay
- `subaructl` workflow polish and developer wrappers
# subaructl
# subaructl
