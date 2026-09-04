"""
Live audio pipeline: system audio (WASAPI loopback) -> sherpa-onnx streaming
ASR -> partial/final transcript, плюс faster-whisper для финальной перепроверки
всей реплики после endpoint.

Логика перенесена из overlay_assistant_live_v4.py практически без изменений —
это рабочий фундамент, который нельзя ломать.
"""

from __future__ import annotations

import os
import queue
import tarfile
import threading
import time
import urllib.request
import warnings
from pathlib import Path

import numpy as np

import config
from utils import push_status

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

SAMPLE_RATE = 16000
READ_MS = 50
BLOCK = SAMPLE_RATE * READ_MS // 1000              # 800 samples = 50 ms
RECORDER_BLOCK = BLOCK * 6                          # WASAPI buffer 300 ms

# Только для визуального индикатора. Endpoint определяет сам streaming ASR.
SILENCE_RMS = 0.00030

SHERPA_MODEL_ROOT = config.SHERPA_MODEL_ROOT
SHERPA_MODEL_DIR = config.SHERPA_MODEL_DIR
SHERPA_MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    f"{config.SHERPA_MODEL_NAME}.tar.bz2"
)


def _find_model_files(model_dir: Path) -> tuple[Path, Path, Path, Path] | None:
    if not model_dir.is_dir():
        return None
    tokens = model_dir / "tokens.txt"
    decoder = model_dir / "decoder.onnx"
    encoder = model_dir / "encoder.int8.onnx"
    joiner = model_dir / "joiner.int8.onnx"
    if all(p.is_file() for p in (tokens, encoder, decoder, joiner)):
        return tokens, encoder, decoder, joiner
    # fp32 fallback, если пользователь положил не-int8 вариант.
    encoder = model_dir / "encoder.onnx"
    joiner = model_dir / "joiner.onnx"
    if all(p.is_file() for p in (tokens, encoder, decoder, joiner)):
        return tokens, encoder, decoder, joiner
    return None


def ensure_sherpa_model(status_q: queue.Queue) -> tuple[Path, Path, Path, Path] | None:
    found = _find_model_files(SHERPA_MODEL_DIR)
    if found:
        return found

    SHERPA_MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    archive = SHERPA_MODEL_ROOT / f"{config.SHERPA_MODEL_NAME}.tar.bz2"
    push_status(status_q, f"нет streaming-модели RU — скачиваю {config.SHERPA_MODEL_NAME}…")

    try:
        last_report = [-10]

        def progress(blocks: int, block_size: int, total: int) -> None:
            if total <= 0:
                return
            done = min(blocks * block_size, total)
            pct = done * 100 // total
            bucket = (pct // 10) * 10
            if bucket >= last_report[0] + 10:
                last_report[0] = bucket
                status_q.put(("status", f"модель RU: загрузка {bucket}%"))

        urllib.request.urlretrieve(SHERPA_MODEL_URL, archive, reporthook=progress)
        push_status(status_q, "модель RU скачана — распаковываю…")
        with tarfile.open(archive, "r:bz2") as tar:
            tar.extractall(SHERPA_MODEL_ROOT)
        try:
            archive.unlink()
        except OSError:
            pass
    except Exception as e:  # noqa: BLE001
        push_status(status_q, f"не удалось скачать streaming-модель: {e}")
        print("URL:", SHERPA_MODEL_URL, flush=True)
        return None

    found = _find_model_files(SHERPA_MODEL_DIR)
    if not found:
        push_status(status_q, f"в {SHERPA_MODEL_DIR} не найдены model files")
    return found


class StreamingSTT(threading.Thread):
    """Настоящий online recognizer.

    Аудио поступает каждые 50 мс в один долгоживущий stream. Текущий результат
    считывается после каждого декодируемого блока. Нет нарезки на отдельные
    1-секундные WAV-фрагменты и нет переопределения языка.
    """

    def __init__(self, ui_q: queue.Queue, refine_q: queue.Queue):
        super().__init__(daemon=True)
        self.ui_q = ui_q
        self.refine_q = refine_q
        self.stop_evt = threading.Event()
        self.level = 0.0
        self.threshold = SILENCE_RMS

    def run(self) -> None:
        try:
            import soundcard as sc
            import sherpa_onnx
        except ImportError as e:
            push_status(self.ui_q, f"нет зависимости: {e.name}")
            return

        files = ensure_sherpa_model(self.ui_q)
        if not files:
            return
        tokens, encoder, decoder, joiner = files

        push_status(self.ui_q, "гружу streaming ASR RU…")
        try:
            recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=str(tokens),
                encoder=str(encoder),
                decoder=str(decoder),
                joiner=str(joiner),
                num_threads=max(1, min(4, (os.cpu_count() or 2) // 2)),
                sample_rate=SAMPLE_RATE,
                feature_dim=80,
                enable_endpoint_detection=True,
                # Быстрый финал: ~0.7-0.9 с тишины после реплики.
                rule1_min_trailing_silence=1.0,
                rule2_min_trailing_silence=0.7,
                rule3_min_utterance_length=30.0,
                decoding_method="greedy_search",
                provider="cpu",
                model_type="zipformer2",
            )
        except Exception as e:  # noqa: BLE001
            push_status(self.ui_q, f"sherpa-onnx: {e}")
            return

        mic = self._open_loopback(sc)
        if mic is None:
            return

        try:
            from soundcard import SoundcardRuntimeWarning
            warnings.filterwarnings(
                "once", message="data discontinuity in recording", category=SoundcardRuntimeWarning
            )
        except Exception:
            pass

        stream = recognizer.create_stream()
        utterance_id = 1
        utter_audio: list[np.ndarray] = []
        last_text = ""
        last_print = ""
        last_level_print = time.time()
        peak = 0.0

        push_status(self.ui_q, "готов — настоящий LIVE RU STT")

        try:
            with mic.recorder(samplerate=SAMPLE_RATE, blocksize=RECORDER_BLOCK) as rec:
                while not self.stop_evt.is_set():
                    frame = rec.record(numframes=BLOCK)
                    mono = np.asarray(frame, dtype=np.float32)
                    if mono.ndim > 1:
                        # Loopback channels are usually L/R. Mean preserves mono speech;
                        # no per-chunk peak normalization is applied.
                        mono = mono.mean(axis=1)
                    if config.INPUT_GAIN != 1.0:
                        mono = np.clip(mono * config.INPUT_GAIN, -1.0, 1.0)

                    self.level = float(np.sqrt(np.mean(mono * mono))) if mono.size else 0.0
                    peak = max(peak, self.level)
                    utter_audio.append(mono.copy())

                    stream.accept_waveform(SAMPLE_RATE, mono)
                    while recognizer.is_ready(stream):
                        recognizer.decode_stream(stream)

                    result = " ".join(recognizer.get_result(stream).split()).strip()
                    if result != last_text:
                        last_text = result
                        self.ui_q.put(("transcript_partial", (utterance_id, result)))
                        if result and result != last_print:
                            print(f"  LIVE #{utterance_id}: {result}", flush=True)
                            last_print = result

                    if recognizer.is_endpoint(stream):
                        final_text = result
                        if final_text:
                            print(f"  ENDPOINT #{utterance_id}: {final_text}", flush=True)
                            self.ui_q.put(("transcript_final", (utterance_id, final_text)))

                        if final_text and utter_audio:
                            audio = np.concatenate(utter_audio).astype(np.float32, copy=False)
                            # Не блокируем live decoder: full-phrase Whisper идёт в другом потоке.
                            try:
                                self.refine_q.put_nowait((utterance_id, audio))
                            except queue.Full:
                                pass

                        recognizer.reset(stream)
                        utterance_id += 1
                        utter_audio = []
                        last_text = ""
                        last_print = ""
                        self.ui_q.put(("transcript_partial", (utterance_id, "")))

                    now = time.time()
                    if now - last_level_print >= 2.0:
                        print(
                            f"  уровень: пик {peak:.5f} / индикатор {SILENCE_RMS:.5f}",
                            flush=True,
                        )
                        peak = 0.0
                        last_level_print = now
        except Exception as e:  # noqa: BLE001
            push_status(self.ui_q, f"аудио/streaming STT: {e}")

    def _open_loopback(self, sc):
        try:
            mics = sc.all_microphones(include_loopback=True)
        except Exception as e:  # noqa: BLE001
            push_status(self.ui_q, f"нет доступа к аудиоустройствам: {e}")
            return None

        print("--- источники записи ---", flush=True)
        for i, m in enumerate(mics):
            flag = "LOOPBACK" if getattr(m, "isloopback", False) else "микрофон"
            print(f"  [{i}] {flag:<9} {m.name}", flush=True)
        try:
            default = str(sc.default_speaker().name)
        except Exception:
            default = ""
        print(f"  вывод по умолчанию: {default or '?'}", flush=True)
        print("------------------------", flush=True)

        if config.LOOPBACK_DEVICE:
            for m in mics:
                if config.LOOPBACK_DEVICE.lower() in m.name.lower():
                    push_status(self.ui_q, f"слушаю: {m.name}")
                    return m
            push_status(self.ui_q, f"LOOPBACK_DEVICE «{config.LOOPBACK_DEVICE}» не найден")

        loops = [m for m in mics if getattr(m, "isloopback", False)]
        for m in loops:
            a, b = m.name.lower(), default.lower()
            if default and (a in b or b in a):
                push_status(self.ui_q, f"слушаю: {m.name}")
                return m
        if loops:
            push_status(self.ui_q, f"слушаю: {loops[0].name} (fallback)")
            return loops[0]

        push_status(self.ui_q, "loopback-устройство не найдено")
        return None

    def stop(self) -> None:
        self.stop_evt.set()


class WhisperRefiner(threading.Thread):
    def __init__(self, in_q: queue.Queue, ui_q: queue.Queue):
        super().__init__(daemon=True)
        self.in_q = in_q
        self.ui_q = ui_q
        self.stop_evt = threading.Event()

    def run(self) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            push_status(self.ui_q, "нет faster-whisper — live будет работать без финальной коррекции")
            return

        push_status(self.ui_q, f"гружу Whisper-корректор «{config.WHISPER_MODEL}» ({config.WHISPER_LANG})…")
        try:
            model = WhisperModel(
                config.WHISPER_MODEL, device=config.WHISPER_DEVICE, compute_type=config.WHISPER_COMPUTE
            )
        except Exception as e:  # noqa: BLE001
            push_status(self.ui_q, f"Whisper-корректор: {e}")
            return
        push_status(self.ui_q, "Whisper-корректор готов")

        while not self.stop_evt.is_set():
            try:
                uid, audio = self.in_q.get(timeout=0.3)
            except queue.Empty:
                continue

            started = time.perf_counter()
            try:
                segments, _ = model.transcribe(
                    audio,
                    language=config.WHISPER_LANG,
                    task="transcribe",
                    beam_size=5,
                    best_of=5,
                    vad_filter=True,
                    condition_on_previous_text=True,
                    without_timestamps=True,
                    temperature=0.0,
                )
                text = " ".join(s.text.strip() for s in segments).strip()
                text = " ".join(text.split())
            except Exception as e:  # noqa: BLE001
                push_status(self.ui_q, f"финальная коррекция: {e}")
                continue

            elapsed = time.perf_counter() - started
            if text:
                print(f"  REFINE #{uid} ({elapsed:.2f}с): {text}", flush=True)
                self.ui_q.put(("transcript_refined", (uid, text)))

    def stop(self) -> None:
        self.stop_evt.set()
