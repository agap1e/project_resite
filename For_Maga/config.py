"""
Централизованная конфигурация.

Все секреты и параметры окружения читаются из .env (см. .env.example).
Ничего чувствительного не хранится в исходном коде.
"""

from __future__ import annotations

import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def _load_dotenv() -> str | None:
    """Ищет .env начиная с папки скрипта и поднимаясь вверх по дереву."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    start = SCRIPT_DIR
    for _ in range(7):
        candidate = start / ".env"
        if candidate.is_file():
            if load_dotenv is not None:
                load_dotenv(candidate, override=False)
            else:
                _manual_parse_env(candidate)
            return str(candidate)
        if start.parent == start:
            break
        start = start.parent
    return None


def _manual_parse_env(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.split(" #", 1)[0].strip().strip('"\'')
            os.environ.setdefault(key.strip(), value)


ENV_PATH = _load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# --- Claude / Anthropic --------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5").strip() or "claude-sonnet-5"
ANTHROPIC_PROXY = (
    os.environ.get("ANTHROPIC_PROXY")
    or os.environ.get("ALL_PROXY")
    or os.environ.get("HTTPS_PROXY")
    or ""
).strip()

# --- Audio / ASR -----------------------------------------------------------

LOOPBACK_DEVICE = os.environ.get("LOOPBACK_DEVICE", "").strip()
INPUT_GAIN = float(os.environ.get("INPUT_GAIN", "1.0") or "1.0")

SHERPA_MODEL_NAME = os.environ.get(
    "SHERPA_MODEL",
    "sherpa-onnx-streaming-zipformer-small-ru-vosk-int8-2025-08-16",
).strip()
SHERPA_MODEL_ROOT = Path(os.environ.get("SHERPA_MODEL_DIR", SCRIPT_DIR / "models"))
SHERPA_MODEL_DIR = SHERPA_MODEL_ROOT / SHERPA_MODEL_NAME

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small").strip() or "small"
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu").strip() or "cpu"
WHISPER_COMPUTE = os.environ.get(
    "WHISPER_COMPUTE", "float16" if WHISPER_DEVICE == "cuda" else "int8"
).strip()
WHISPER_LANG = os.environ.get("WHISPER_LANG", "ru").strip() or "ru"

# --- Screenshot --------------------------------------------------------

SCREENSHOT_MONITOR = int(os.environ.get("SCREENSHOT_MONITOR", "1") or "1")
SCREENSHOT_MODE = (os.environ.get("SCREENSHOT_MODE", "full").strip().lower() or "full")

TEMP_DIR = SCRIPT_DIR / "temp"
IMAGE_PATH = str(TEMP_DIR / "screenshot_latest.png")
CROPPED_PATH = str(TEMP_DIR / "screenshot_cropped.png")

# --- Telegram (optional, disabled by default) ---------------------------

TELEGRAM_ENABLED = _get_bool("TELEGRAM_ENABLED", False)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_SEND_AUDIO = _get_bool("TELEGRAM_SEND_AUDIO", True)
TELEGRAM_SEND_SCREEN = _get_bool("TELEGRAM_SEND_SCREEN", True)
TELEGRAM_SEND_SCREENSHOT = _get_bool("TELEGRAM_SEND_SCREENSHOT", False)
