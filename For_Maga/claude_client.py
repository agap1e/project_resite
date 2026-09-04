import base64
import mimetypes
import socket

from anthropic import Anthropic

from config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_PROXY,
    CLAUDE_MODEL,
    IMAGE_PATH,
)

DEFAULT_LOCAL_PROXY = "socks5://127.0.0.1:10808"


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


EXAM_PROMPT = """
На изображении находится экзаменационный билет, содержащий два теоретических вопроса.

Внимательно распознай точные формулировки обоих вопросов и подготовь подробный ответ на каждый из них.

Требования к ответу:

1. Отвечай на русском языке.
2. Разбери оба вопроса отдельно и удели им примерно одинаковое внимание.
3. Сохрани точную формулировку каждого вопроса в заголовке.
4. Дай содержательный и логически связный ответ, подходящий для устного ответа на экзамене.
5. Не ограничивайся краткими определениями и перечислением терминов.
6. Объясняй смысл понятий, основные принципы, устройство, этапы работы, особенности и взаимосвязи.
7. Если это уместно, приводи небольшие практические примеры.
8. Если вопрос содержит несколько частей, обязательно ответь на каждую из них.
9. Используй правильную профессиональную терминологию, но объясняй материал понятным языком.
10. Не добавляй неподтверждённые факты и не придумывай содержание, которого нет в вопросе.
11. Не упоминай изображение, распознавание текста или процесс подготовки ответа.
12. Избегай лишних вступлений, повторов и общих фраз. Пиши подробно, но по существу.
13. Не трать почти весь объём на первый вопрос. Оставь достаточно места для полноценного ответа на второй.
14. Если отдельный фрагмент вопроса невозможно прочитать, отметь только этот фрагмент как неразборчивый и не пытайся его выдумать.

Используй следующий формат:

Вопрос 1. <точная формулировка первого вопроса>

<Подробный связный ответ из нескольких содержательных абзацев>

Вопрос 2. <точная формулировка второго вопроса>

<Подробный связный ответ из нескольких содержательных абзацев>

Выведи только готовые ответы на два вопроса без дополнительных комментариев.
""".strip()


# Один Anthropic-клиент на весь период работы программы.
_proxy = _resolve_proxy()
if _proxy:
    import httpx
    client = Anthropic(api_key=ANTHROPIC_API_KEY, http_client=httpx.Client(proxy=_proxy, timeout=180.0))
else:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)


def send_image_to_claude(image_path: str) -> str:
    # Автоматически определяем тип изображения
    media_type, _ = mimetypes.guess_type(image_path)

    supported_media_types = {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
    }

    if media_type not in supported_media_types:
        media_type = "image/png"

    # Читаем изображение и кодируем его в Base64
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(
            image_file.read()
        ).decode("utf-8")

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXAM_PROMPT,
                    },
                ],
            }
        ],
    )

    # Берём только текстовые блоки.
    # ThinkingBlock и другие служебные блоки пропускаются.
    text_blocks = []

    for block in response.content:
        if getattr(block, "type", None) == "text":
            block_text = getattr(block, "text", "")

            if block_text:
                text_blocks.append(block_text)

    if text_blocks:
        return "\n\n".join(text_blocks).strip()

    raise RuntimeError(
        "Claude не вернул текстовый ответ. "
        f"stop_reason={response.stop_reason}, "
        f"content={response.content}"
    )


if __name__ == "__main__":
    try:
        answer = send_image_to_claude(IMAGE_PATH)

        print()
        print("Ответ Claude:")
        print(answer)

    except Exception as error:
        print()
        print("ОШИБКА:")
        print(type(error).__name__, error)