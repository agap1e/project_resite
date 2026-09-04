"""
Screenshot pipeline: mss -> overwrite temp file -> (опционально) legacy
Moodle-обрезка -> Claude Vision.

По умолчанию SCREENSHOT_MODE=full - Claude получает весь монитор целиком.
SCREENSHOT_MODE=moodle сохраняет старую специализированную обрезку
(crop_question.py) как опциональный legacy-режим.

Файлы не накапливаются: используется overwrite (temp/screenshot_latest.png,
temp/screenshot_cropped.png), а не отдельный файл на каждый снимок.
"""

from __future__ import annotations

from pathlib import Path

import mss
import mss.tools

import config

TEMP_DIR = config.TEMP_DIR
SCREENSHOT_PATH = Path(config.IMAGE_PATH)
CROPPED_PATH = Path(config.CROPPED_PATH)


def ensure_temp_dir() -> None:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def capture_screenshot(monitor: int | None = None) -> Path:
    """Снимает скриншот указанного монитора (blocking, вызывать из worker-потока)."""
    ensure_temp_dir()
    monitor_index = monitor if monitor is not None else config.SCREENSHOT_MONITOR
    with mss.MSS() as sct:
        monitors = sct.monitors
        idx = monitor_index if 0 <= monitor_index < len(monitors) else 1
        shot = sct.grab(monitors[idx])
        mss.tools.to_png(shot.rgb, shot.size, output=str(SCREENSHOT_PATH))
    return SCREENSHOT_PATH


def prepare_for_vision(mode: str | None = None) -> Path:
    """Возвращает путь к изображению, которое нужно отправить Claude Vision."""
    effective_mode = (mode or config.SCREENSHOT_MODE).strip().lower()
    if effective_mode == "moodle":
        from crop_question import crop_question, fallback_crop

        try:
            crop_question(SCREENSHOT_PATH, CROPPED_PATH)
        except Exception:
            fallback_crop(SCREENSHOT_PATH, CROPPED_PATH)
        return CROPPED_PATH
    return SCREENSHOT_PATH
