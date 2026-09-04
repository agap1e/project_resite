"""
Overlay Assistant v4 — unified app
==================================

Два независимых канала Claude поверх одного discreet overlay:

  AUDIO:  system audio (WASAPI loopback) -> sherpa-onnx streaming ASR
          -> faster-whisper refine -> ClaudeAudioWorker -> "CLAUDE — AUDIO"
  SCREEN: global hotkey/кнопка -> mss screenshot -> ClaudeVisionWorker
          -> "CLAUDE — SCREEN"
  DOCUMENTS: PDF/DOCX/TXT/MD -> DocumentContextManager -> релевантный
          контекст для обоих каналов Claude.

Ни один pipeline не блокирует другой — у каждого свой поток и своя очередь.

Хоткеи:
  Ctrl+Alt+Space  -> отправить текущую расшифровку в Claude (AUDIO)
  Ctrl+Alt+Enter  -> FORCE: прервать текущий AUDIO-ответ и отправить заново
  Ctrl+Alt+S      -> скриншот -> Claude Vision (SCREEN)
  Ctrl+Alt+O      -> добавить документы
  Ctrl+Alt+H      -> скрыть/показать overlay
  Ctrl+Alt+Q      -> выход
"""

from __future__ import annotations

import importlib.util
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog

import config
import screenshot_service
from audio_service import SILENCE_RMS, StreamingSTT, WhisperRefiner
from claude_service import ClaudeAudioWorker, ClaudeVisionWorker
from document_context import DocumentContextManager
from telegram_service import TelegramWorker
from utils import push_status
from win_capture import apply_capture_exclusion

TRANSCRIPT_CHARS = 2800
WINDOW_W, WINDOW_H = 920, 640
OPACITY = 0.92

SCREEN_USER_INSTRUCTION = (
    "Проанализируй изображение на скриншоте и дай содержательный ответ согласно инструкции."
)

BG = "#12141a"
BG_SOFT = "#1b1e27"
BG_PANEL = "#181b23"
FG = "#e8eaf0"
FG_DIM = "#7d8496"
ACCENT = "#6ea8fe"
ACCENT2 = "#f2a65a"
ERR = "#ef6a6a"


class OverlayApp:
    def __init__(self) -> None:
        self.ui_q: queue.Queue = queue.Queue()
        self.refine_q: queue.Queue = queue.Queue(maxsize=4)

        self.final_by_uid: dict[int, str] = {}
        self.uid_order: list[int] = []
        self.live_uid = 1
        self.live_text = ""
        self.audio_busy = False
        self.screen_busy = False
        self.hidden = False

        self.doc_manager = DocumentContextManager()
        self.doc_ids: list[str] = []  # parallel to docs_list rows

        self._build_window()
        self.auto = tk.BooleanVar(master=self.root, value=False)
        self._build_widgets()

        self.streaming = StreamingSTT(self.ui_q, self.refine_q)
        self.refiner = WhisperRefiner(self.refine_q, self.ui_q)
        self.claude_audio = ClaudeAudioWorker(self.ui_q, self.doc_manager)
        self.claude_vision = ClaudeVisionWorker(self.ui_q, self.doc_manager)
        self.telegram = TelegramWorker(self.ui_q)

        self.streaming.start()
        self.refiner.start()
        self.claude_audio.start()
        self.claude_vision.start()
        self.telegram.start()

        self._hotkey_handles: list = []
        self._register_hotkeys()
        self.root.after(40, self._pump)
        self.root.after(2000, self._keep_on_top)

    # ------------------------------------------------------------------
    # Window / widgets
    # ------------------------------------------------------------------

    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("Overlay Assistant v4")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", OPACITY)
        self.root.configure(bg=BG)
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+{sw-WINDOW_W-40}+40")
        self.root.update_idletasks()
        _, self.capture_status = apply_capture_exclusion(self.root)

    def _build_widgets(self) -> None:
        bar = tk.Frame(self.root, bg=BG_SOFT, height=34)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        bar.bind("<Button-1>", self._drag_start)
        bar.bind("<B1-Motion>", self._drag_move)

        self.dot = tk.Label(bar, text="●", bg=BG_SOFT, fg=FG_DIM, font=("Segoe UI", 9))
        self.dot.pack(side="left", padx=(10, 4))
        title = tk.Label(
            bar, text="Overlay Assistant v4", bg=BG_SOFT, fg=FG,
            font=("Segoe UI Semibold", 10)
        )
        title.pack(side="left")
        title.bind("<Button-1>", self._drag_start)
        title.bind("<B1-Motion>", self._drag_move)

        self.lvl = tk.Label(bar, text="0.0000", bg=BG_SOFT, fg=FG_DIM, font=("Consolas", 8))
        self.lvl.pack(side="left", padx=8)
        tk.Button(
            bar, text="✕", bg=BG_SOFT, fg=FG_DIM, bd=0,
            activebackground=BG_SOFT, command=self.quit
        ).pack(side="right", padx=8)
        tk.Checkbutton(
            bar, text="авто", variable=self.auto, bg=BG_SOFT, fg=FG_DIM,
            selectcolor=BG_SOFT, activebackground=BG_SOFT, bd=0,
        ).pack(side="right")

        self._build_documents_bar()

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=(4, 0))
        main.columnconfigure(0, weight=1, uniform="cols")
        main.columnconfigure(1, weight=1, uniform="cols")
        main.rowconfigure(0, weight=1)

        self._build_audio_panel(main)
        self._build_screen_panel(main)

        self.status = tk.Label(
            self.root, text=self.capture_status, bg=BG, fg=FG_DIM,
            font=("Segoe UI", 8), anchor="w", wraplength=WINDOW_W - 24, justify="left"
        )
        self.status.pack(side="bottom", fill="x", padx=12, pady=(4, 8))

    def _build_documents_bar(self) -> None:
        docs_bar = tk.Frame(self.root, bg=BG)
        docs_bar.pack(fill="x", padx=12, pady=(8, 4))

        tk.Label(
            docs_bar, text="DOCUMENTS", bg=BG, fg=FG_DIM,
            font=("Segoe UI", 7), anchor="w"
        ).pack(anchor="w")

        row = tk.Frame(docs_bar, bg=BG)
        row.pack(fill="x", pady=(2, 0))

        list_frame = tk.Frame(row, bg=BG_SOFT)
        list_frame.pack(side="left", fill="x", expand=True)
        self.docs_list = tk.Listbox(
            list_frame, height=3, bg=BG_SOFT, fg=FG, bd=0,
            highlightthickness=0, selectbackground=ACCENT, selectforeground="#0b0d12",
            font=("Segoe UI", 9), activestyle="none",
        )
        self.docs_list.pack(fill="x", padx=6, pady=4)

        btns = tk.Frame(row, bg=BG)
        btns.pack(side="left", padx=(8, 0))
        tk.Button(
            btns, text="Добавить файлы  Ctrl+Alt+O", bg=BG_SOFT, fg=FG, bd=0,
            font=("Segoe UI", 8), command=self.add_documents
        ).pack(fill="x", pady=1)
        tk.Button(
            btns, text="Удалить выбранный", bg=BG_SOFT, fg=FG_DIM, bd=0,
            font=("Segoe UI", 8), command=self.remove_selected_document
        ).pack(fill="x", pady=1)
        tk.Button(
            btns, text="Очистить все", bg=BG_SOFT, fg=FG_DIM, bd=0,
            font=("Segoe UI", 8), command=self.clear_documents
        ).pack(fill="x", pady=1)

    def _build_audio_panel(self, parent: tk.Frame) -> None:
        col = tk.Frame(parent, bg=BG_PANEL)
        col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        tk.Label(
            col, text="AUDIO", bg=BG_PANEL, fg=ACCENT,
            font=("Segoe UI Semibold", 9), anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        btn_row = tk.Frame(col, bg=BG_PANEL)
        btn_row.pack(fill="x", padx=10)
        tk.Button(
            btn_row, text="Отправить  Ctrl+Alt+Space", bg=ACCENT, fg="#0b0d12",
            bd=0, font=("Segoe UI Semibold", 9), command=self.ask_now
        ).pack(side="left", ipadx=7, ipady=4)
        tk.Button(
            btn_row, text="FORCE", bg=BG_SOFT, fg=FG, bd=0,
            font=("Segoe UI Semibold", 8), command=self.force_send
        ).pack(side="left", padx=6, ipadx=6, ipady=4)
        tk.Button(
            btn_row, text="Очистить", bg=BG_SOFT, fg=FG_DIM, bd=0,
            command=self.clear_audio
        ).pack(side="left", ipadx=6, ipady=4)

        tk.Label(
            col, text="СЛЫШУ — LIVE", bg=BG_PANEL, fg=FG_DIM,
            font=("Segoe UI", 7), anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))
        self.tr_view = tk.Text(
            col, width=1, height=5, bg=BG_SOFT, fg=FG_DIM, bd=0,
            wrap="word", font=("Segoe UI", 10), padx=8, pady=6,
            highlightthickness=0, state="disabled"
        )
        self.tr_view.pack(fill="x", padx=10)

        tk.Label(
            col, text="CLAUDE — AUDIO", bg=BG_PANEL, fg=ACCENT,
            font=("Segoe UI", 7), anchor="w"
        ).pack(fill="x", padx=10, pady=(10, 2))
        self.ans_view = tk.Text(
            col, width=1, height=1, bg=BG_SOFT, fg=FG, bd=0,
            wrap="word", font=("Segoe UI", 11), padx=10, pady=8,
            highlightthickness=0, state="disabled"
        )
        self.ans_view.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _build_screen_panel(self, parent: tk.Frame) -> None:
        col = tk.Frame(parent, bg=BG_PANEL)
        col.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        tk.Label(
            col, text="SCREENSHOT", bg=BG_PANEL, fg=ACCENT2,
            font=("Segoe UI Semibold", 9), anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        btn_row = tk.Frame(col, bg=BG_PANEL)
        btn_row.pack(fill="x", padx=10)
        tk.Button(
            btn_row, text="Screenshot  Ctrl+Alt+S", bg=ACCENT2, fg="#0b0d12",
            bd=0, font=("Segoe UI Semibold", 9), command=self.take_screenshot
        ).pack(side="left", ipadx=7, ipady=4)
        tk.Button(
            btn_row, text="Очистить", bg=BG_SOFT, fg=FG_DIM, bd=0,
            command=self.clear_screen
        ).pack(side="left", padx=6, ipadx=6, ipady=4)

        self.screen_status = tk.Label(
            col, text="SCREEN STATUS: ожидание", bg=BG_PANEL, fg=FG_DIM,
            font=("Segoe UI", 7), anchor="w"
        )
        self.screen_status.pack(fill="x", padx=10, pady=(8, 2))

        tk.Label(
            col, text="CLAUDE — SCREEN", bg=BG_PANEL, fg=ACCENT2,
            font=("Segoe UI", 7), anchor="w"
        ).pack(fill="x", padx=10, pady=(4, 2))
        self.screen_ans_view = tk.Text(
            col, width=1, height=1, bg=BG_SOFT, fg=FG, bd=0,
            wrap="word", font=("Segoe UI", 11), padx=10, pady=8,
            highlightthickness=0, state="disabled"
        )
        self.screen_ans_view.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _drag_start(self, e) -> None:
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e) -> None:
        self.root.geometry(f"+{e.x_root-self._dx}+{e.y_root-self._dy}")

    def _keep_on_top(self) -> None:
        self.root.attributes("-topmost", True)
        self.root.after(2000, self._keep_on_top)

    # ------------------------------------------------------------------
    # Hotkeys
    # ------------------------------------------------------------------

    def _register_hotkeys(self) -> None:
        self.root.bind("<Control-Alt-space>", lambda e: self.ask_now())
        try:
            import keyboard
            bindings = {
                "ctrl+alt+space": self.ask_now,
                "ctrl+alt+enter": self.force_send,
                "ctrl+alt+s": self.take_screenshot,
                "ctrl+alt+o": self.add_documents,
                "ctrl+alt+h": self.toggle_hide,
                "ctrl+alt+q": self.quit,
            }
            for combo, fn in bindings.items():
                handle = keyboard.add_hotkey(combo, (lambda f=fn: self.root.after(0, f)))
                self._hotkey_handles.append(handle)
        except Exception as e:  # noqa: BLE001
            push_status(self.ui_q, f"глобальные хоткеи недоступны: {e}")

    def _unregister_hotkeys(self) -> None:
        try:
            import keyboard
            for handle in self._hotkey_handles:
                try:
                    keyboard.remove_hotkey(handle)
                except (KeyError, ValueError):
                    pass
        except Exception:
            pass

    def toggle_hide(self) -> None:
        if self.hidden:
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            _, self.capture_status = apply_capture_exclusion(self.root)
            self.status.config(text=self.capture_status)
        else:
            self.root.withdraw()
        self.hidden = not self.hidden

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def add_documents(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Добавить документы",
            filetypes=[
                ("Документы (PDF/DOCX/TXT/MD)", "*.pdf *.docx *.txt *.md"),
                ("Все файлы", "*.*"),
            ],
        )
        if not paths:
            return
        push_status(self.ui_q, f"загрузка {len(paths)} документ(ов)…")
        threading.Thread(target=self._add_documents_worker, args=(list(paths),), daemon=True).start()

    def _add_documents_worker(self, paths: list[str]) -> None:
        try:
            self.doc_manager.add_files(paths)
        except Exception as e:  # noqa: BLE001
            self.ui_q.put(("status", f"документы: {type(e).__name__}: {e}"))
        self.ui_q.put(("documents_updated", None))

    def remove_selected_document(self) -> None:
        sel = self.docs_list.curselection()
        if not sel:
            return
        for idx in sel:
            if idx < len(self.doc_ids):
                self.doc_manager.remove_file(self.doc_ids[idx])
        self._refresh_documents()

    def clear_documents(self) -> None:
        self.doc_manager.clear()
        self._refresh_documents()

    def _refresh_documents(self) -> None:
        docs = self.doc_manager.list_documents()
        self.doc_ids = [d.doc_id for d in docs]
        self.docs_list.delete(0, "end")
        for d in docs:
            if d.status == "ok":
                marker = "ok"
            elif d.status == "error":
                marker = f"ошибка: {d.error}"
            elif d.status == "empty":
                marker = "пусто"
            else:
                marker = "…"
            self.docs_list.insert("end", f"{d.display_name}  [{marker}]")
        names = ", ".join(d.display_name for d in docs) if docs else "нет"
        self.status.config(text=f"Documents: {names}")

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    def _context(self) -> str:
        parts = [self.final_by_uid[u] for u in self.uid_order if self.final_by_uid.get(u)]
        if self.live_text:
            parts.append(self.live_text)
        return " ".join(parts)[-TRANSCRIPT_CHARS:].strip()

    def ask_now(self) -> None:
        text = self._context()
        if text:
            self.claude_audio.ask(text, interrupt=self.audio_busy)

    def force_send(self) -> None:
        text = self._context()
        if not text:
            self.status.config(text="FORCE: пока нет текста")
            return
        self.claude_audio.ask(text, interrupt=True)
        self.status.config(text="FORCE: текущий LIVE-текст отправлен")

    def clear_audio(self) -> None:
        self.final_by_uid.clear()
        self.uid_order.clear()
        self.live_text = ""
        self._set_text(self.tr_view, "")
        self._set_text(self.ans_view, "")

    def _render_transcript(self) -> None:
        parts = [self.final_by_uid[u] for u in self.uid_order if self.final_by_uid.get(u)]
        if self.live_text:
            parts.append(self.live_text)
        self._set_text(self.tr_view, " ".join(parts)[-850:])
        self.tr_view.see("end")

    def _on_partial(self, uid: int, text: str) -> None:
        self.live_uid = uid
        self.live_text = text
        self._render_transcript()

    def _on_final(self, uid: int, text: str) -> None:
        if uid not in self.uid_order:
            self.uid_order.append(uid)
        self.final_by_uid[uid] = text
        if self.live_uid == uid:
            self.live_text = ""
        self.uid_order[:] = self.uid_order[-40:]
        self._render_transcript()

        if self.auto.get() and not self.audio_busy and self._looks_like_question(text):
            self.ask_now()

    def _on_refined(self, uid: int, text: str) -> None:
        # Whisper replaces the rough streaming final for this utterance.
        if uid not in self.uid_order:
            self.uid_order.append(uid)
        old = self.final_by_uid.get(uid, "")
        self.final_by_uid[uid] = text
        self._render_transcript()
        if old != text:
            self.status.config(text=f"Whisper уточнил реплику #{uid}")

    @staticmethod
    def _looks_like_question(text: str) -> bool:
        t = text.lower().strip()
        if "?" in t:
            return True
        return t.startswith((
            "что", "как", "почему", "зачем", "когда", "где", "кто", "какой",
            "какая", "какие", "расскажи", "объясни"
        ))

    # ------------------------------------------------------------------
    # Screenshot / Vision
    # ------------------------------------------------------------------

    def take_screenshot(self) -> None:
        if self.screen_busy:
            self.screen_status.config(text="SCREEN STATUS: предыдущий запрос ещё обрабатывается…")
        self._set_text(self.screen_ans_view, "")
        self.screen_status.config(text="SCREEN STATUS: снимаю скриншот…")
        threading.Thread(target=self._screenshot_worker, daemon=True).start()

    def clear_screen(self) -> None:
        self._set_text(self.screen_ans_view, "")
        self.screen_status.config(text="SCREEN STATUS: ожидание")

    def _screenshot_worker(self) -> None:
        try:
            screenshot_service.capture_screenshot()
            image_path = screenshot_service.prepare_for_vision()
        except Exception as e:  # noqa: BLE001
            self.ui_q.put(("screen_status", f"ошибка скриншота: {type(e).__name__}: {e}"))
            return

        self.ui_q.put(("screen_status", "скриншот готов — отправляю в Claude Vision…"))
        if config.TELEGRAM_SEND_SCREENSHOT:
            self.telegram.send_photo(str(image_path), caption="Screenshot")
        self.claude_vision.ask(str(image_path), SCREEN_USER_INSTRUCTION)

    # ------------------------------------------------------------------
    # Event pump (Tkinter main thread)
    # ------------------------------------------------------------------

    def _pump(self) -> None:
        try:
            while True:
                kind, payload = self.ui_q.get_nowait()
                if kind == "status":
                    self.status.config(text=payload)
                elif kind == "transcript_partial":
                    self._on_partial(*payload)
                elif kind == "transcript_final":
                    self._on_final(*payload)
                elif kind == "transcript_refined":
                    self._on_refined(*payload)
                elif kind == "audio_answer_start":
                    self.audio_busy = True
                    self._set_text(self.ans_view, "")
                elif kind == "audio_answer_chunk":
                    self._append(self.ans_view, payload)
                elif kind == "audio_answer_end":
                    self.audio_busy = False
                    if config.TELEGRAM_SEND_AUDIO:
                        text = self.ans_view.get("1.0", "end").strip()
                        if text:
                            self.telegram.send_text(text)
                elif kind == "screen_answer_start":
                    self.screen_busy = True
                    self._set_text(self.screen_ans_view, "")
                elif kind == "screen_answer_chunk":
                    self._append(self.screen_ans_view, payload)
                elif kind == "screen_answer_end":
                    self.screen_busy = False
                    if config.TELEGRAM_SEND_SCREEN:
                        text = self.screen_ans_view.get("1.0", "end").strip()
                        if text:
                            self.telegram.send_text(text)
                elif kind == "screen_status":
                    self.screen_status.config(text=f"SCREEN STATUS: {payload}")
                elif kind == "documents_updated":
                    self._refresh_documents()
        except queue.Empty:
            pass

        level = getattr(self.streaming, "level", 0.0)
        active = level > SILENCE_RMS
        self.dot.config(fg=ACCENT if active else FG_DIM)
        self.lvl.config(text=f"{level:.4f}", fg=ACCENT if active else FG_DIM)
        self.root.after(40, self._pump)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def quit(self) -> None:
        self._unregister_hotkeys()
        self.streaming.stop()
        self.refiner.stop()
        self.claude_audio.stop()
        self.claude_vision.stop()
        self.telegram.stop()
        for path in (screenshot_service.SCREENSHOT_PATH, screenshot_service.CROPPED_PATH):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        self.root.destroy()

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    @staticmethod
    def _append(widget: tk.Text, text: str) -> None:
        widget.config(state="normal")
        widget.insert("end", text)
        widget.see("end")
        widget.config(state="disabled")

    def run(self) -> None:
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def preflight() -> None:
    from claude_service import PROXY, PROXY_SOURCE

    print("=" * 66)
    print(f"Python        : {sys.version.split()[0]} ({sys.executable})")
    print(f".env          : {config.ENV_PATH or 'не найден'}")
    key = config.ANTHROPIC_API_KEY
    print(f"API key       : {'есть, длина ' + str(len(key)) if key else 'НЕТ'}")
    print(f"Claude proxy  : {PROXY or 'нет'} [{PROXY_SOURCE}]")
    print(f"LIVE ASR      : sherpa-onnx / {config.SHERPA_MODEL_NAME}")
    print(f"Final ASR     : faster-whisper / {config.WHISPER_MODEL} / lang={config.WHISPER_LANG}")
    print(f"Screenshot    : monitor={config.SCREENSHOT_MONITOR}, mode={config.SCREENSHOT_MODE}")
    print(f"Telegram      : {'включён' if config.TELEGRAM_ENABLED else 'выключен'}")
    for mod, why in (
        ("numpy", "обязателен"),
        ("soundcard", "loopback"),
        ("sherpa_onnx", "настоящий streaming STT"),
        ("faster_whisper", "финальное уточнение"),
        ("anthropic", "Claude"),
        ("keyboard", "глобальные хоткеи"),
        ("socksio", "SOCKS proxy"),
        ("mss", "screenshot"),
        ("pypdf", "чтение PDF-документов"),
        ("docx", "чтение DOCX-документов (python-docx)"),
        ("sklearn", "TF-IDF retrieval по документам"),
    ):
        ok = importlib.util.find_spec(mod) is not None
        print(f"{mod:<15}: {'ok' if ok else 'НЕ УСТАНОВЛЕН — ' + why}")
    print("=" * 66, flush=True)


if __name__ == "__main__":
    preflight()
    OverlayApp().run()
