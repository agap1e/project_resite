"""
Два независимых Claude worker-а поверх одной сети/прокси-конфигурации:

  ClaudeAudioWorker  -> текстовые запросы по live-транскрипту.
  ClaudeVisionWorker -> запросы Claude Vision по скриншоту.

Каждый работает в своём потоке со своей очередью, поэтому долгий Vision-запрос
(до ~15с) никогда не блокирует Audio pipeline и наоборот.
"""

from __future__ import annotations

import base64
import mimetypes
import queue
import socket
import threading

import config
from document_context import DocumentContextManager

DEFAULT_LOCAL_PROXY = "socks5://127.0.0.1:10808"

AUDIO_SYSTEM_PROMPT = (
    "Ты — ассистент, работающий в реальном времени. На вход ты получаешь "
    "расшифровку русской речи с компьютера пользователя. В ней возможны ошибки ASR. "
    "Восстанавливай смысл по контексту. Отвечай на последний заданный вопрос. "
    "Сначала 1-2 предложения сути, затем при необходимости до 5 коротких пунктов. "
    "Без вступлений.\n\n"
    "Если запрос содержит блок <user_documents> — это документы пользователя. "
    "Используй факты из них, только когда они релевантны вопросу. Не выдумывай "
    "информацию, которой нет в документах. Если документы не подключены или "
    "нерелевантны текущему вопросу — отвечай на основе обычных знаний."
)

SCREEN_SYSTEM_PROMPT = (
    "Проанализируй содержимое изображения. Определи вопрос, задачу, текст, код, "
    "интерфейс или другую важную информацию.\n"
    "Если на изображении есть вопрос или задача — дай полезный содержательный ответ.\n"
    "Если подключены пользовательские документы (блок <user_documents>) и они "
    "релевантны запросу, используй их как дополнительный контекст.\n"
    "Не придумывай информацию, которой нет в пользовательских документах.\n"
    "Если документы нерелевантны — отвечай на основе обычных знаний."
)


def local_proxy_is_up(host: str = "127.0.0.1", port: int = 10808) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.15):
            return True
    except OSError:
        return False


def resolve_proxy() -> tuple[str, str]:
    configured = (config.ANTHROPIC_PROXY or "").strip()
    if configured:
        return configured, "config/.env"
    if local_proxy_is_up():
        return DEFAULT_LOCAL_PROXY, "авто: 127.0.0.1:10808"
    return "", "прямое соединение"


PROXY, PROXY_SOURCE = resolve_proxy()


def make_client(proxy: str, status_cb=None):
    from anthropic import Anthropic

    if not proxy:
        return Anthropic(api_key=config.ANTHROPIC_API_KEY)
    try:
        import httpx
        if proxy.startswith("socks"):
            import socksio  # noqa: F401
        try:
            hc = httpx.Client(proxy=proxy, timeout=180.0)
        except TypeError:
            hc = httpx.Client(proxies=proxy, timeout=180.0)
        if status_cb:
            status_cb(f"Claude proxy: {proxy}")
        return Anthropic(api_key=config.ANTHROPIC_API_KEY, http_client=hc)
    except Exception as e:  # noqa: BLE001
        if status_cb:
            status_cb(f"прокси Claude: {e}")
        return None


def build_prompt_text(doc_context: str, body: str) -> str:
    if doc_context:
        return f"<user_documents>\n{doc_context}\n</user_documents>\n\n{body}"
    return body


class ClaudeAudioWorker(threading.Thread):
    def __init__(self, ui_q: queue.Queue, doc_manager: DocumentContextManager | None = None):
        super().__init__(daemon=True)
        self.ui_q = ui_q
        self.doc_manager = doc_manager
        self.req_q: queue.Queue[str] = queue.Queue()
        self.stop_evt = threading.Event()
        self.cancel_current = threading.Event()
        self.client = None

    def run(self) -> None:
        if not config.ANTHROPIC_API_KEY:
            self.ui_q.put(("status", "нет ANTHROPIC_API_KEY в .env"))
            return
        self.client = make_client(PROXY, lambda m: self.ui_q.put(("status", m)))
        if self.client is None:
            return

        while not self.stop_evt.is_set():
            try:
                text = self.req_q.get(timeout=0.3)
            except queue.Empty:
                continue
            self._ask(text)

    def _stream(self, text: str, doc_context: str) -> None:
        body = f"<transcript>\n{text}\n</transcript>\n\nОтветь на последний вопрос."
        prompt = build_prompt_text(doc_context, body)
        with self.client.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=700,
            system=AUDIO_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                if self.stop_evt.is_set() or self.cancel_current.is_set():
                    break
                self.ui_q.put(("audio_answer_chunk", chunk))

    def _ask(self, text: str) -> None:
        self.cancel_current.clear()
        self.ui_q.put(("audio_answer_start", None))

        doc_context = ""
        if self.doc_manager is not None:
            try:
                doc_context = self.doc_manager.get_context(text)
            except Exception as e:  # noqa: BLE001
                self.ui_q.put(("status", f"document context: {e}"))

        try:
            self._stream(text, doc_context)
        except Exception as e:  # noqa: BLE001
            code = getattr(e, "status_code", "?")
            print(f"[API audio] {type(e).__name__} status={code}", flush=True)

            if str(code) == "403" and not PROXY and local_proxy_is_up():
                try:
                    self.ui_q.put(("status", "403 напрямую -> повтор через SOCKS 10808"))
                    self.client = make_client(DEFAULT_LOCAL_PROXY, lambda m: self.ui_q.put(("status", m)))
                    if self.client is not None:
                        self._stream(text, doc_context)
                        self.ui_q.put(("audio_answer_end", None))
                        return
                except Exception as retry_e:  # noqa: BLE001
                    e = retry_e
                    code = getattr(retry_e, "status_code", "?")

            self.ui_q.put(("audio_answer_chunk", f"\n[ошибка API {code}: {e}]"))
        self.ui_q.put(("audio_answer_end", None))

    def ask(self, text: str, *, interrupt: bool = False) -> None:
        if interrupt:
            self.cancel_current.set()
            try:
                while True:
                    self.req_q.get_nowait()
            except queue.Empty:
                pass
        self.req_q.put(text)

    def stop(self) -> None:
        self.stop_evt.set()


class ClaudeVisionWorker(threading.Thread):
    def __init__(self, ui_q: queue.Queue, doc_manager: DocumentContextManager | None = None):
        super().__init__(daemon=True)
        self.ui_q = ui_q
        self.doc_manager = doc_manager
        self.req_q: queue.Queue[tuple[str, str]] = queue.Queue()
        self.stop_evt = threading.Event()
        self.client = None

    def run(self) -> None:
        if not config.ANTHROPIC_API_KEY:
            self.ui_q.put(("screen_status", "нет ANTHROPIC_API_KEY в .env"))
            return
        self.client = make_client(PROXY, lambda m: self.ui_q.put(("status", m)))
        if self.client is None:
            return

        while not self.stop_evt.is_set():
            try:
                image_path, instruction = self.req_q.get(timeout=0.3)
            except queue.Empty:
                continue
            self._ask(image_path, instruction)

    @staticmethod
    def _image_block(image_path: str) -> dict:
        media_type, _ = mimetypes.guess_type(image_path)
        supported = {"image/png", "image/jpeg", "image/webp", "image/gif"}
        if media_type not in supported:
            media_type = "image/png"
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}

    def _stream(self, image_path: str, instruction: str, doc_context: str) -> None:
        text = build_prompt_text(doc_context, instruction)
        content = [self._image_block(image_path), {"type": "text", "text": text}]
        with self.client.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=1500,
            system=SCREEN_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            for chunk in stream.text_stream:
                if self.stop_evt.is_set():
                    break
                self.ui_q.put(("screen_answer_chunk", chunk))

    def _ask(self, image_path: str, instruction: str) -> None:
        self.ui_q.put(("screen_answer_start", None))
        self.ui_q.put(("screen_status", "отправка в Claude Vision…"))

        doc_context = ""
        if self.doc_manager is not None:
            try:
                # Вопрос по картинке заранее неизвестен - берём компромиссный
                # общий контекст (см. document_context.get_context, Вариант A).
                doc_context = self.doc_manager.get_context("")
            except Exception as e:  # noqa: BLE001
                self.ui_q.put(("status", f"document context: {e}"))

        try:
            self._stream(image_path, instruction, doc_context)
            self.ui_q.put(("screen_status", "готово"))
        except Exception as e:  # noqa: BLE001
            code = getattr(e, "status_code", "?")
            print(f"[API vision] {type(e).__name__} status={code}", flush=True)

            if str(code) == "403" and not PROXY and local_proxy_is_up():
                try:
                    self.ui_q.put(("status", "403 напрямую -> повтор через SOCKS 10808"))
                    self.client = make_client(DEFAULT_LOCAL_PROXY, lambda m: self.ui_q.put(("status", m)))
                    if self.client is not None:
                        self._stream(image_path, instruction, doc_context)
                        self.ui_q.put(("screen_status", "готово"))
                        self.ui_q.put(("screen_answer_end", None))
                        return
                except Exception as retry_e:  # noqa: BLE001
                    e = retry_e
                    code = getattr(retry_e, "status_code", "?")

            self.ui_q.put(("screen_answer_chunk", f"\n[ошибка API {code}: {e}]"))
            self.ui_q.put(("screen_status", f"ошибка: {code}"))
        self.ui_q.put(("screen_answer_end", None))

    def ask(self, image_path: str, instruction: str) -> None:
        self.req_q.put((image_path, instruction))

    def stop(self) -> None:
        self.stop_evt.set()
