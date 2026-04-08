# Repository Guidelines

## Project Structure & Module Organization
`/opt/subaru` is a multi-project Subaru tooling workspace rather than a single packaged app. Use the root for shared operations and runbooks: `README.md`, `OPERATOR_RUNBOOK.md`, `subaructl`, `logging/`, `wrxdash/`, and hardware-facing scripts. The main Python projects are `imprezadash/` (PyQt dashboard, tests in `imprezadash/tests/`) and `obdai/` (Poetry package with source in `obdai/src/` and tests in `obdai/tests/`). ECU flashing and firmware tooling live under `FastECU/`, `tactrix/`, `wrxflash/`, and `ecuextractor/`. Keep new code close to the owning subsystem; avoid adding more root-level one-off scripts unless they are shared operator entrypoints.

## Build, Test, and Development Commands
Use the documented root workflow first:

- `./subaructl doctor` checks devices, Python modules, permissions, and dashboard reachability.
- `SUBARU_SSM_PORT=/dev/ttyACM0 SUBARU_SSM_BAUD=9600 python3 logging/ssm_logger_csv.py` starts the SSM CSV logger.
- `SUBARU_ELM327_PORT=/dev/rfcomm0 python3 wrxdash/app.py` starts the Flask dashboard.
- `cd imprezadash && ./install_env.sh && ./run_tests.sh` sets up the local venv and runs dashboard tests.
- `cd imprezadash && ./build_pyinstaller.sh` builds the packaged executable.
- `cd obdai && poetry install && poetry run pytest --cov=src` installs dependencies and runs the OBD AI test suite.

## Coding Style & Naming Conventions
Python is the default language. Use 4-space indentation, `snake_case` for functions/modules, `PascalCase` for classes, and explicit, descriptive script names such as `ssm_logger_csv.py`. Prefer small, testable modules over route-heavy or script-heavy files. Format with Black; use Ruff, Flake8, isort, and mypy where configured by each subproject (`imprezadash/pyproject.toml`, `obdai/pyproject.toml`).

## Testing Guidelines
Pytest is the common test runner. Put tests under each project’s `tests/` directory and name files `test_*.py`. Mirror the module or workflow under test, for example `test_flash_integration.py` for ECU flashing flows. Mock serial, OBD, and device access whenever possible; do not require live hardware for routine CI-style validation.

## Commit & Pull Request Guidelines
The workspace root does not have a shared Git history; the nested `FastECU` history uses short, imperative subjects such as `Rename ...` and `Update ...`. Follow that style: one-line imperative summaries, optionally prefixed by subsystem, for example `wrxdash: tighten reconnect logging`. PRs should describe the affected subsystem, user-visible behavior, hardware assumptions, and exact verification steps. Include screenshots for dashboard UI changes and note any serial device or ROM prerequisites.
