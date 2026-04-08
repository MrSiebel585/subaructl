# Subaru Codebase Recommendations

## Executive Summary
This document provides recommendations for improving code quality, architecture, and performance across the Subaru project codebase.

---

## IMPLEMENTATION PROGRESS

### ✅ COMPLETED
| Task | Status | Files |
|------|--------|-------|
| Centralized configuration module | DONE | `subaru_config/` |
| Logging utilities with throttling | DONE | `subaru_config/logging_utils.py` |
| Unit tests for config module | DONE | `subaru_config/test_settings.py` (10 tests) |
| OBDReader class | DONE | `wrxdash/obd_service.py` |
| Unit tests for OBD service | DONE | `wrxdash/test_obd_service.py` (11 tests) |

---

## 1. Code Quality Improvements

### 1.1 Type Hints (High Priority)
**Current State**: Inconsistent use of type hints across modules.

**Recommendations**:
- Add comprehensive type hints to all function signatures
- Use `typing` module for complex types (List, Dict, Optional, Union)
- Consider using `mypy` for static type checking

**Files to Update**:
- `wrxdash/obd_reader.py` - Add types to all functions
- `wrxdash/telemetry.py` - Add return types and parameter types
- `logging/ssm_logger_csv.py` - Add types to `ssm_request()`, `parse_rpm()`, etc.

**Example**:
```python
# Before
def parse_rpm(resp):
    if len(resp) < 9:
        return None
    
# After
def parse_rpm(resp: bytes) -> Optional[float]:
    if len(resp) < 9:
        return None
```

### 1.2 Replace Print Statements with Logging Framework ⚠️ PENDING
**Current State**: Using `print()` for all output across 46+ locations.

**Files to Update**:
- `wrxdash/obd_reader.py` (11 prints)
- `wrxdash/app.py` (14 prints)
- `wrxdash/ssm_reader.py` (6 prints)
- `logging/ssm_logger_csv.py` (9 prints)
- `logging/ssm_sweep_logger.py` (9 prints)
- `logging/ssm_ai_logger.py` (10 prints)

**Use the new logging utilities**:
```python
from subaru_config import obd_logger, ssm_logger

# Replace print("[+] Logging started") with:
obd_logger.info("Logging started: %s", path)

# Use LogThrottler for repeated warnings:
from subaru_config import LogThrottler
throttler = LogThrottler(interval=20)
throttler.log("missing_port", obd_logger.warning, "Device missing: %s", port)
```

### 1.3 Improve Exception Handling
**Current State**: Broad `except Exception:` clauses that hide errors.

**Recommendations**:
- Catch specific exceptions
- Add proper error propagation
- Log exception details before re-raising or handling

**Example**:
```python
# Before
except Exception as e:
    print(f"[!] OBD query error on {label}: {e}")
    data[label] = None

# After
except obd.OBDResponseError as e:
    obd_logger.warning("OBD response error for %s: %s", label, e)
    data[label] = None
except serial.SerialException as e:
    obd_logger.error("Serial communication error: %s", e)
    connection = None  # Trigger reconnection
except Exception as e:
    obd_logger.exception("Unexpected error querying %s", label)
    data[label] = None
```

### 1.4 Remove Global Mutable State ⚠️ PENDING
**Current State**: Heavy use of global variables in modules like `obd_reader.py`.

**Recommendations**:
- Use classes to encapsulate state
- Implement dependency injection
- Use thread-local storage for thread-specific data

**Example**:
```python
# Before (obd_reader.py)
connection = None
is_logging = False

# After
class OBDReader:
    def __init__(self, port: str):
        self._connection = None
        self._is_logging = False
        self._port = port
```

---

## 2. Architecture Improvements

### 2.1 Implement Configuration Management ✅ DONE
**Status**: Centralized config module created at `subaru_config/`

**Usage**:
```python
from subaru_config import get_settings

settings = get_settings()
print(settings.elm327.port)  # /dev/rfcomm0 (or from env)
print(settings.dashboard.port)  # 8080 (or from env)
```

**Environment Variables Supported**:
- `SUBARU_SSM_PORT`, `SUBARU_SSM_BAUD`
- `SUBARU_ELM327_PORT`, `SUBARU_ELM327_BAUD`, `SUBARU_ELM327_FAST`
- `SUBARU_LOG_DIR`
- `SUBARU_DASH_HOST`, `SUBARU_DASH_PORT`, `SUBARU_DASH_URL`
- `SUBARU_ECU_DEFS_PATH`, `SUBARU_ROM_UPLOAD_DIR`
- `SUBARU_SECRET_KEY`

### 2.2 Add Dependency Injection ⚠️ PENDING
**Current State**: Direct imports and instantiation within functions.

**Recommendations**:
- Use a DI container or simple factory pattern
- Make dependencies injectable for easier testing

### 2.3 Separate Concerns in Flask App ⚠️ PENDING
**Current State**: `wrxdash/app.py` mixes routing, business logic, and data handling.

**Proposed Structure**:
```
wrxdash/
  routes/
    __init__.py
    logs.py       # Log-related endpoints
    replay.py     # Replay endpoints
    rom.py        # ROM upload/analyze endpoints
  services/
    obd_service.py
    ssm_service.py
    telemetry_service.py
```

### 2.4 Add Graceful Shutdown Handling ⚠️ PENDING
**Current State**: Daemon threads started without cleanup.

**Recommendations**:
- Implement proper thread lifecycle management
- Add signal handlers for SIGTERM/SIGINT
- Use `threading.Event` for graceful shutdown

---

## 3. Performance Optimizations

### 3.1 Parallel OBD Queries ⚠️ PENDING
**Current State**: Sequential queries with sleep delays.

**Recommendations**:
- Use `concurrent.futures.ThreadPoolExecutor` for parallel queries
- Batch commands where possible
- Reduce unnecessary sleep delays

**Example**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def read_parallel(commands: Dict[str, OBDCommand]) -> Dict[str, float]:
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(connection.query, cmd): name 
                  for name, cmd in commands.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result().value.magnitude
            except Exception:
                results[name] = None
    return results
```

### 3.2 Add Caching for Expensive Operations ⚠️ PENDING
**Current State**: Repeated calculations without caching.

**Recommendations**:
- Cache ROM metadata after first read
- Use `functools.lru_cache` for pure functions

**Example**:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_rom_metadata(rom_path: str) -> ROMMetadata:
    """Cache ROM metadata to avoid re-parsing."""
    rom = ROM(rom_path)
    return ROMMetadata(
        rom_id=extract_rom_id(rom.data),
        size=rom.size,
        checksum=validate_checksum(rom.data)
    )
```

### 3.3 Use Database for Large Log Files ⚠️ PENDING
**Current State**: CSV files for logging (not scalable).

**Recommendations**:
- Use SQLite for local storage
- Consider PostgreSQL for long-term analysis
- Implement log rotation

### 3.4 Optimize Serial Communication ⚠️ PENDING
**Current State**: Fixed delays regardless of response time.

**Recommendations**:
- Use event-driven serial reading
- Implement request-response pattern with timeouts
- Reduce unnecessary delays

---

## 4. Testing Recommendations

### 4.1 Add Unit Tests ✅ PARTIAL
**Current State**: Basic tests for config module (10 tests passing).

**To Add**:
- Tests for ROM parsing
- Tests for telemetry data transformation
- Tests for OBD command handling (with mocks)

### 4.2 Add Integration Tests ⚠️ PENDING
**Recommendations**:
- Test Flask routes with test client
- Test OBD connection flow (with mocked device)
- Test replay functionality

---

## 5. Documentation Improvements

### 5.1 Add Docstrings ⚠️ PENDING
**Recommendations**:
- Add Google-style docstrings to all public functions
- Document parameters, return values, and exceptions

### 5.2 API Documentation ⚠️ PENDING
**Recommendations**:
- Add OpenAPI/Swagger for Flask endpoints
- Document environment variables
- Add README sections for each major component

---

## Priority Implementation Plan

| Priority | Task | Status |
|----------|------|--------|
| HIGH | Centralized configuration | ✅ DONE |
| HIGH | Real-time Alert System | ✅ DONE |
| HIGH | Replace print with logging | ⚠️ PENDING |
| HIGH | Improve exception handling | ⚠️ PENDING |
| HIGH | Add type hints | ⚠️ PENDING |
| MEDIUM | Implement OBDReader class | ⚠️ PENDING |
| MEDIUM | Add parallel OBD queries | ⚠️ PENDING |
| MEDIUM | Add more unit tests | ⚠️ PENDING |
| LOW | Database backend for logs | ⚠️ PENDING |
| LOW | Refactor Flask app structure | ⚠️ PENDING |
| LOW | Add graceful shutdown | ⚠️ PENDING |

---

## Summary

### Completed ✅
- **Configuration module** (`subaru_config/`) with:
  - Type-safe settings using dataclasses
  - Environment variable support
  - Singleton pattern for global access
- **Logging utilities** with:
  - Standardized logger setup
  - Log throttling to prevent spam
  - Component-specific loggers
- **OBDReader class** (`wrxdash/obd_service.py`) with:
  - Encapsulated state (no globals)
  - Proper error handling
  - Logging integration
  - Legacy compatibility functions
- **Real-time Alert System** (`wrxdash/alerts.py`) with:
  - Configurable thresholds for critical engine parameters
  - Default thresholds for: Coolant Temp, Boost, RPM, Voltage, IAT, Engine Load, Knock
  - Three severity levels: Info, Warning, Critical
  - Cooldown system to prevent alert spam
  - REST API for threshold management
  - SocketIO integration for real-time alerts
  - Web UI for configuration (`/alerts`)
  - Alert history tracking
- **Unit tests** (37 tests passing: 21 config + 16 alerts)
- **Improved ECU Menu** (`ecumenu`) with:
  - Fixed syntax errors and proper bash structure
  - 11 menu options (was 9)
  - New options: Launch WRX Dash, SSM Logger, OBD AI, ECU Extractor, Logs, System Info
  - Better device detection and diagnostics
  - Doctor command for troubleshooting
  - Color-coded output with better UX

### Remaining Work
The codebase still needs:
1. **Logging migration** - Replace 46+ print statements with proper logging
2. **Type hints** - Add type annotations to core modules
3. **OBDReader class** - Encapsulate global state
4. **Exception handling** - Catch specific exceptions
5. **Performance** - Parallel queries and caching
6. **More tests** - Coverage for core functionality

Start with the high-priority items for immediate improvements, then proceed to medium and low priority items as time permits.

