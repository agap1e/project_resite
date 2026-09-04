import keyboard

from datetime import datetime

from Telega import *
from crop_question import *
from claude_client import *
from config import IMAGE_PATH, CROPPED_PATH
from screenshot_service import capture_screenshot

SCREENSHOT_PATH = IMAGE_PATH


def take_screenshot():
    capture_screenshot()

    print(
        f"[{datetime.now():%H:%M:%S}] "
        "Скриншот сделан"
    )


def process():

    try:
        print("\n--- Начало обработки ---")

        # 1. Скриншот
        take_screenshot()

        try:
            crop_question(
                SCREENSHOT_PATH,
                CROPPED_PATH
            )

            print("Moodle-обрезка успешна")

        except Exception as crop_error:
            print("Moodle-обрезка не удалась:")
            print(crop_error)

            fallback_crop(
                SCREENSHOT_PATH,
                CROPPED_PATH
            )

        # 3. Claude
        answer = send_image_to_claude(
            str(CROPPED_PATH)
        )
        send_photo(
            str(CROPPED_PATH),
            caption="Экзаменационный билет"
        )

        send_text(answer)

        print("\nОтвет Claude:")
        print(answer)

        print("--- Готово ---")

    except Exception as e:
        print("\nОШИБКА:")
        print(type(e).__name__, e)


print("Программа запущена")
print("F8  — обработать вопрос")
print("F10 — выйти")

keyboard.add_hotkey(
    "F8",
    process
)

keyboard.wait("F10")