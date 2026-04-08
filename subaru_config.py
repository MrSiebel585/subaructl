import os


def _env(name, default):
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name, default):
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_int_list(name, default):
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    try:
        parsed = [int(v.strip()) for v in value.split(",") if v.strip()]
        return parsed or default
    except ValueError:
        return default


LOG_DIR = _env("SUBARU_LOG_DIR", "/home/wrx/logs")
SYSTEM_LOG_DIR = _env("SUBARU_SYSTEM_LOG_DIR", "/opt/logs/system")
SECRET_KEY = _env("SUBARU_SECRET_KEY", "secret!")
SSM_PORT = _env("SUBARU_SSM_PORT", "/dev/ttyACM0")
SSM_BAUD_RATES = _env_int_list("SUBARU_SSM_BAUD_RATES", [9600, 4800])
SSM_BAUD = _env_int("SUBARU_SSM_BAUD", SSM_BAUD_RATES[0] if SSM_BAUD_RATES else 9600)
ELM327_PORT = _env("SUBARU_ELM327_PORT", "/dev/rfcomm0")
ELM327_BAUD = _env_int("SUBARU_ELM327_BAUD", 9600)
OLLAMA_URL = _env("SUBARU_OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = _env("SUBARU_OLLAMA_MODEL", "tinyllama")
