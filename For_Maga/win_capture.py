"""
Screen-capture exclusion для overlay-окна на Windows.

Использует штатный WinAPI SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE).
Это официальный флаг Windows, предназначенный именно для исключения окна из
совместимых screen-capture pipeline (например, стандартного захвата экрана и
Windows Graphics Capture на Windows 10 2004+). Никакого сокрытия процесса,
инъекций или обхода систем безопасности здесь нет и не должно быть.
"""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk

WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011


def get_hwnd(root: tk.Tk) -> int:
    root.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
    return hwnd or root.winfo_id()


def apply_capture_exclusion(root: tk.Tk) -> tuple[bool, str]:
    """Применяет исключение окна из screen capture.

    Возвращает (success, human-readable статус). Должна вызываться после
    создания окна и повторно после каждого deiconify()/show().
    """
    if sys.platform != "win32":
        return False, "Capture exclusion: N/A (доступно только на Windows)"
    try:
        hwnd = get_hwnd(root)
        u32 = ctypes.windll.user32
        if u32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
            return True, "Capture exclusion: ACTIVE"
        if u32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR):
            return False, "Capture exclusion: FAILED (fallback: чёрный прямоугольник в записи)"
        return False, "Capture exclusion: FAILED"
    except Exception as e:  # noqa: BLE001
        return False, f"Capture exclusion: FAILED ({type(e).__name__}: {e})"
