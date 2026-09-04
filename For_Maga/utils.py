"""Небольшие общие утилиты, используемые несколькими модулями."""

from __future__ import annotations

import queue
import time


def push_status(q: "queue.Queue", msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    q.put(("status", msg))
