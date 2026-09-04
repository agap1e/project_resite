import socket

import requests

from config import (
    ANTHROPIC_PROXY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)


DEFAULT_LOCAL_PROXY = "socks5h://127.0.0.1:10808"
MAX_MESSAGE_LENGTH = 4000


def _local_proxy_is_up(host: str = "127.0.0.1", port: int = 10808) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.15):
            return True
    except OSError:
        return False


def _resolve_proxy() -> str:
    if ANTHROPIC_PROXY:
        return ANTHROPIC_PROXY
    if _local_proxy_is_up():
        return DEFAULT_LOCAL_PROXY
    return ""


session = requests.Session()

_proxy = _resolve_proxy()
if _proxy:
    session.proxies.update({"http": _proxy, "https": _proxy})


def _require_credentials() -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID не заданы в .env"
        )


def check_response(response: requests.Response) -> dict:
    if not response.ok:
        raise RuntimeError(
            f"Ошибка Telegram {response.status_code}: "
            f"{response.text}"
        )

    return response.json()


def split_text(text: str, max_length: int = MAX_MESSAGE_LENGTH):
    """
    Делит длинный текст на части.
    Сначала пытается разделить по абзацам,
    затем по пробелам, чтобы не разрывать слова.
    """

    remaining_text = text.strip()

    while len(remaining_text) > max_length:
        split_position = remaining_text.rfind(
            "\n",
            0,
            max_length + 1,
        )

        # Если подходящего переноса строки нет,
        # пытаемся разделить по последнему пробелу
        if split_position < max_length // 2:
            split_position = remaining_text.rfind(
                " ",
                0,
                max_length + 1,
            )

        # Если нет ни переноса, ни пробела
        if split_position <= 0:
            split_position = max_length

        message_part = remaining_text[:split_position].strip()

        if message_part:
            yield message_part

        remaining_text = remaining_text[split_position:].strip()

    if remaining_text:
        yield remaining_text


def send_photo(image_path: str, caption: str = "") -> dict:
    """
    Отправляет фотографию.
    Caption можно использовать только для короткой подписи.
    """

    _require_credentials()

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    )

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
    }

    if caption:
        # У подписи фотографии лимит 1024 символа
        data["caption"] = caption[:1024]

    with open(image_path, "rb") as photo:
        response = session.post(
            url,
            data=data,
            files={
                "photo": photo,
            },
            timeout=60,
        )

    return check_response(response)


def send_text(text: str) -> list:
    """
    Отправляет текст отдельными сообщениями.
    Длинный ответ автоматически делится на части.
    """

    if not text or not text.strip():
        raise ValueError("Нельзя отправить пустой текст")

    _require_credentials()

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    results = []

    for message_part in split_text(text):
        response = session.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message_part,
            },
            timeout=60,
        )

        results.append(check_response(response))

    return results