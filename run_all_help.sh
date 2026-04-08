#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_list() {
  cat <<'EOF'
Available projects/commands:
  1) wrxdash: install deps
  2) wrxdash: run dashboard (port 8080)
  3) ecu_extractor: extract ROM -> JSON
  4) ecu_extractor: diff two extracted JSON files
  5) ecu_extractor: safety audit ROM directory
  6) imprezadash: install deps
  7) imprezadash: run PyQt app
  8) obdai: install deps
  9) obdai: run Streamlit HUD (port 8501)
  10) wrxloggerwarningsystem: install deps
  11) wrxloggerwarningsystem: run mock logger
  12) wrxloggerwarningsystem: run Tkinter GUI
  13) ssm: install base deps
  14) ssm: run SSM AI dash (port 8080)
  15) ssm: run ELM327 AI dash (port 8080)
  16) tactrix: install pyserial
  17) tactrix: run tactrix logger
  18) tactrix: run full sweep logger
  19) tactrix: run tactrix ai logger
  20) wrxecuripper: extract maps from local bins
  21) logging: run SSM CSV logger
EOF
}

print_examples() {
  cat <<'EOF'
Examples:
  ./run_all_help.sh list
  ./run_all_help.sh run 2
  ./run_all_help.sh
EOF
}

run_id() {
  local id="${1:-}"
  case "$id" in
    1)  (cd "$ROOT_DIR" && python3 -m pip install -r wrxdash/requirements.txt) ;;
    2)  (cd "$ROOT_DIR" && SUBARU_ELM327_PORT=/dev/rfcomm0 python3 wrxdash/app.py) ;;
    3)  (cd "$ROOT_DIR/ecu_extractor" && python3 cli.py /path/to/rom.bin --defs /path/to/ecu_defs.xml --out rom_analysis.json) ;;
    4)  (cd "$ROOT_DIR/ecu_extractor" && python3 diff_cli.py stock.json tuned.json --out diff_output.json) ;;
    5)  (cd "$ROOT_DIR/ecu_extractor" && python3 safety_cli.py /path/to/roms --out safety_audit.json) ;;
    6)  (cd "$ROOT_DIR" && python3 -m pip install -r imprezadash/requirements.txt) ;;
    7)  (cd "$ROOT_DIR" && python3 imprezadash/main.py) ;;
    8)  (cd "$ROOT_DIR" && python3 -m pip install -r obdai/requirements.txt) ;;
    9)  (cd "$ROOT_DIR/obdai/scripts" && streamlit run hud_obdai.py --server.port 8501) ;;
    10) (cd "$ROOT_DIR" && python3 -m pip install -r wrxloggerwarningsystem/requirements.txt) ;;
    11) (cd "$ROOT_DIR" && python3 wrxloggerwarningsystem/logger_backend.py) ;;
    12) (cd "$ROOT_DIR" && python3 wrxloggerwarningsystem/tkinter_gui.py) ;;
    13) (cd "$ROOT_DIR" && python3 -m pip install pyserial flask flask-socketio requests) ;;
    14) (cd "$ROOT_DIR" && SUBARU_SSM_PORT=/dev/ttyACM0 python3 ssm/ssm_ai_dash.py) ;;
    15) (cd "$ROOT_DIR" && SUBARU_ELM327_PORT=/dev/rfcomm0 python3 ssm/ssm_ai_dash_elm327.py) ;;
    16) (cd "$ROOT_DIR" && python3 -m pip install pyserial) ;;
    17) (cd "$ROOT_DIR" && SUBARU_SSM_PORT=/dev/ttyACM0 python3 tactrix/logging/tactrix.py) ;;
    18) (cd "$ROOT_DIR" && python3 tactrix/logging/tactrix_logger_full.py) ;;
    19) (cd "$ROOT_DIR" && python3 tactrix/logging/tactrix_ai.py) ;;
    20) (cd "$ROOT_DIR/wrxecuripper" && python3 src/extract_maps.py) ;;
    21) (cd "$ROOT_DIR" && SUBARU_SSM_PORT=/dev/ttyACM0 SUBARU_SSM_BAUD=9600 python3 logging/ssm_logger_csv.py) ;;
    *)
      echo "Unknown id: $id" >&2
      print_list
      exit 1
      ;;
  esac
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    list)
      print_list
      ;;
    run)
      if [[ $# -lt 2 ]]; then
        echo "Missing id for 'run'." >&2
        print_examples
        exit 1
      fi
      run_id "$2"
      ;;
    "" )
      print_list
      echo
      read -r -p "Enter id to run (or press Enter to exit): " selected
      if [[ -n "${selected:-}" ]]; then
        run_id "$selected"
      fi
      ;;
    -h|--help|help)
      print_list
      echo
      print_examples
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      print_examples
      exit 1
      ;;
  esac
}

main "$@"
