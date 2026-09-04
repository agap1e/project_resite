import cv2
from PIL import Image


def crop_question(input_path, output_path):
    img = cv2.imread(str(input_path))

    if img is None:
        raise FileNotFoundError(input_path)

    height, width = img.shape[:2]

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower_blue = (90, 80, 80)
    upper_blue = (120, 255, 255)

    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    buttons = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        # Отбрасываем слишком маленькие элементы
        if w < 60 or h < 25:
            continue

        # Отбрасываем слишком большие области
        if w > 400 or h > 100:
            continue

        buttons.append((x, y, w, h))

    print("Найденные синие элементы:")
    for b in sorted(buttons, key=lambda item: item[1]):
        print(b)

    # ---------------------------------------
    # 1. Ищем именно верхнюю кнопку "Назад"
    # ---------------------------------------

    back_candidates = [
        b for b in buttons

        # примерно центральная область страницы по вертикали,
        # но выше самого вопроса
        if height * 0.20 < b[1] < height * 0.45

        # кнопка должна находиться не в левом меню
        and width * 0.15 < b[0] < width * 0.60
    ]

    if not back_candidates:
        raise RuntimeError("Не удалось найти верхнюю кнопку Назад")

    # Если кандидатов несколько, берём самый верхний
    back_button = min(
        back_candidates,
        key=lambda b: b[1]
    )

    bx, by, bw, bh = back_button

    print("Кнопка Назад:", back_button)

    # ---------------------------------------
    # 2. Ищем нижнюю навигацию
    # ---------------------------------------

    bottom_buttons = [
        b for b in buttons

        # должна быть существенно ниже кнопки Назад
        if b[1] > by + 200

        # и находиться в основной области страницы
        and b[0] > width * 0.15
    ]

    if bottom_buttons:
        lowest_button = max(
            bottom_buttons,
            key=lambda b: b[1] + b[3]
        )

        bottom_y = lowest_button[1] + lowest_button[3]

    else:
        # Если нижние кнопки не нашли,
        # берём разумную часть экрана
        bottom_y = int(height * 0.80)

    # ---------------------------------------
    # 3. Формируем область вопроса
    # ---------------------------------------

    x1 = max(0, bx - 20)
    y1 = max(0, by - 15)

    # До почти правого края страницы
    x2 = int(width * 0.98)

    # Немного ниже нижних кнопок
    y2 = min(height, bottom_y + 25)

    print(
        f"Обрезка: ({x1}, {y1}) → ({x2}, {y2})"
    )

    image = Image.open(input_path)

    cropped = image.crop(
        (x1, y1, x2, y2)
    )

    cropped.save(output_path)

    return output_path


def fallback_crop(input_path, output_path):
    image = Image.open(input_path)

    width, height = image.size

    # Убираем браузерную строку и шапку
    y1 = int(height * 0.18)

    cropped = image.crop((
        int(width * 0.15),
        y1,
        width,
        int(height * 0.90)
    ))

    cropped.save(output_path)

    return output_path