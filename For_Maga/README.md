# Overlay Assistant v4

Windows desktop overlay-ассистент с двумя независимыми каналами Claude:

- **AUDIO** — system audio (WASAPI loopback) → sherpa-onnx streaming ASR (live-транскрипт) →
  faster-whisper (финальная перепроверка реплики) → Claude → ответ в панели `CLAUDE — AUDIO`.
- **SCREEN** — скриншот по хоткею/кнопке → Claude Vision → ответ в панели `CLAUDE — SCREEN`.
- **DOCUMENTS** — PDF/DOCX/TXT/MD, локальное извлечение текста и TF-IDF retrieval,
  контекст доступен обоим каналам Claude.

Оба Claude-канала работают в отдельных потоках/очередях и никогда не блокируют друг друга
или live-аудио pipeline.

## Требования

- Windows 10/11 (используется WinAPI `SetWindowDisplayAffinity`)
- Python 3.10+
- Работающее системное аудио (WASAPI loopback устройство)

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Модель sherpa-onnx для русского streaming ASR скачивается автоматически при первом
запуске в `models/` (если её там ещё нет).

## Конфигурация

Скопируйте `.env.example` в `.env` (в этой же папке, `For_Maga/`) и заполните:

```bash
copy .env.example .env
```

Обязательно: `ANTHROPIC_API_KEY`. Остальные переменные опциональны, см. `.env.example`:

- `CLAUDE_MODEL`, `ANTHROPIC_PROXY` — модель и (опциональный) SOCKS/HTTP прокси для Claude.
- `LOOPBACK_DEVICE`, `INPUT_GAIN` — выбор loopback-устройства и усиление входного сигнала.
- `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE` — параметры faster-whisper.
- `SCREENSHOT_MONITOR`, `SCREENSHOT_MODE` — номер монитора и режим обработки скриншота
  (`full` — весь монитор целиком, по умолчанию; `moodle` — legacy-обрезка под старый
  экзаменационный сценарий, см. `crop_question.py`).
- `TELEGRAM_ENABLED` и `TELEGRAM_SEND_*` — опциональная отправка ответов в Telegram,
  по умолчанию выключено.

**Важно:** предыдущая версия `config.py` содержала реальный Anthropic API key и
Telegram bot token в виде обычного текста, и эти значения уже присутствуют в истории
git. Считайте оба секрета скомпрометированными — сгенерируйте новый Anthropic API key
и/или новый Telegram bot token и используйте их только через `.env`.

## Запуск

```bash
python overlay_assistant_live_v4.py
```

(или через `start_hiddenGhost.vbs` для запуска без консоли).

## Хоткеи

| Хоткей | Действие |
|---|---|
| `Ctrl+Alt+Space` | Отправить текущую audio-расшифровку в Claude |
| `Ctrl+Alt+Enter` | FORCE — прервать текущий audio-ответ и отправить заново |
| `Ctrl+Alt+S` | Скриншот → Claude Vision |
| `Ctrl+Alt+O` | Добавить документы (файловый диалог) |
| `Ctrl+Alt+H` | Скрыть/показать overlay |
| `Ctrl+Alt+Q` | Выход |

Пока overlay скрыт (`Ctrl+Alt+H`), audio pipeline, Whisper, оба Claude worker-а и
document context продолжают работать в фоне; ответы сохраняются и видны сразу
после повторного показа окна.

## Документы

Кнопка «Добавить файлы» (или `Ctrl+Alt+O`) открывает стандартный диалог выбора файлов
(multi-select). Поддерживаются `.pdf`, `.docx`, `.txt`, `.md`. Текст извлекается один раз
при загрузке (`DocumentContextManager`, `document_context.py`) и не перечитывается на
каждый запрос к Claude.

Если суммарный объём документов укладывается в ~30 000 символов, весь текст уходит в
Claude целиком. Для больших наборов документов используется локальный TF-IDF +
cosine similarity retrieval (scikit-learn) с fallback на пересечение ключевых слов,
если scikit-learn не установлен — никаких внешних embedding-сервисов.

Документы никогда не привязываются к ответу искусственно: system prompt явно говорит
Claude использовать их только когда они релевантны вопросу и не выдумывать факты.

## Screen-capture exclusion

Overlay-окно исключается из захвата экрана штатным Windows API:
`SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` (`win_capture.py`).

Это официальный флаг Windows, предназначенный именно для этой цели — он не скрывает
процесс, не использует инъекции и не обходит защитное ПО. Overlay uses the Windows
`WDA_EXCLUDEFROMCAPTURE` display-affinity flag so the application window is excluded
from compatible Windows screen-capture pipelines.

Ограничения:
- работает только на Windows (на других ОС — no-op, приложение продолжает работать);
- эффективность зависит от того, какой capture backend использует конкретное ПО для
  захвата экрана — флаг официально поддерживается GDI BitBlt/PrintWindow и Windows
  Graphics Capture на Windows 10 версии 2004+, но это не универсальная гарантия для
  абсолютно любого стороннего механизма захвата.

Статус применения флага отображается в статус-баре при запуске и повторно
проверяется при каждом показе окна после `Ctrl+Alt+H`.

## Структура проекта

| Файл | Назначение |
|---|---|
| `overlay_assistant_live_v4.py` | Точка входа, Tkinter UI, хоткеи, event pump |
| `audio_service.py` | StreamingSTT (sherpa-onnx) + WhisperRefiner (faster-whisper) |
| `claude_service.py` | ClaudeAudioWorker и ClaudeVisionWorker (независимые потоки) |
| `document_context.py` | DocumentContextManager — извлечение текста + retrieval |
| `screenshot_service.py` | Скриншот через mss, legacy Moodle-режим |
| `telegram_service.py` | Опциональная неблокирующая отправка в Telegram |
| `win_capture.py` | `apply_capture_exclusion()` — WDA_EXCLUDEFROMCAPTURE |
| `config.py` | Загрузка `.env` и всех настроек |
| `utils.py` | Общие мелкие утилиты (`push_status`) |
| `main.py`, `claude_client.py`, `crop_question.py`, `Telega.py` | Legacy single-shot screenshot pipeline (F8/F10), сохранён для обратной совместимости |

## Troubleshooting

**Не находится loopback-устройство.** При запуске в консоли выводится список всех
аудиоустройств с пометкой `LOOPBACK`/`микрофон`. Укажите нужное явно через
`LOOPBACK_DEVICE` в `.env` (подстрока имени устройства).

**Claude возвращает 403 напрямую.** Приложение автоматически пробует повторить запрос
через локальный SOCKS-прокси на `127.0.0.1:10808`, если он поднят. Либо явно укажите
`ANTHROPIC_PROXY` в `.env`.

**Скриншот получается пустым/чёрным.** Проверьте `SCREENSHOT_MONITOR` в `.env` —
номер монитора соответствует индексу в `mss().monitors` (0 — виртуальный "весь экран",
1, 2, … — отдельные мониторы).

## Известные ограничения

- Screen-capture exclusion — штатная функция Windows, а не универсальная защита от
  любого способа записи экрана (см. раздел выше).
- Локальный TF-IDF retrieval — простая эвристика, а не семантический поиск; для очень
  разнородных больших документов релевантность может быть не идеальной.
- Legacy Moodle-режим скриншота (`SCREENSHOT_MODE=moodle`, `crop_question.py`) заточен
  под конкретную вёрстку и не гарантированно работает на других интерфейсах.
