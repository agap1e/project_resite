"""
Telegram — опциональная compatibility-функция, выключена по умолчанию
(TELEGRAM_ENABLED=false в .env). Работает в отдельном потоке через очередь,
чтобы сетевые запросы никогда не блокировали Tkinter main thread. Любая
ошибка Telegram логируется в статус-бар и не влияет на остальное приложение.
"""

from __future__ import annotations

import queue
import threading

import config


class TelegramWorker(threading.Thread):
    def __init__(self, ui_q: queue.Queue):
        super().__init__(daemon=True)
        self.ui_q = ui_q
        self.q: queue.Queue[tuple[str, object]] = queue.Queue()
        self.stop_evt = threading.Event()

    def run(self) -> None:
        if not config.TELEGRAM_ENABLED:
            return
        if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
            self.ui_q.put(("status", "Telegram включён, но TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID не заданы"))
            return

        while not self.stop_evt.is_set():
            try:
                kind, payload = self.q.get(timeout=0.3)
            except queue.Empty:
                continue
            try:
                if kind == "text":
                    from Telega import send_text
                    send_text(payload)  # type: ignore[arg-type]
                elif kind == "photo":
                    from Telega import send_photo
                    path, caption = payload  # type: ignore[misc]
                    send_photo(path, caption)
            except Exception as e:  # noqa: BLE001
                self.ui_q.put(("status", f"Telegram: {type(e).__name__}: {e}"))

    def send_text(self, text: str) -> None:
        if config.TELEGRAM_ENABLED and text.strip():
            self.q.put(("text", text))

    def send_photo(self, path: str, caption: str = "") -> None:
        if config.TELEGRAM_ENABLED:
            self.q.put(("photo", (path, caption)))

    def stop(self) -> None:
        self.stop_evt.set()
