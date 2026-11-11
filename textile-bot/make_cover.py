# -*- coding: utf-8 -*-
"""
make_cover.py — обложка объявления Avito (1600×1200) и аватар профиля (800×800).
Запуск: python make_cover.py
"""

import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter

import make_shots as M

W, H = 1600, 1200
BG1, BG2 = (10, 18, 26), (22, 38, 52)
ACCENT = (91, 192, 235)
WHITE = (236, 244, 250)
MUTED = (132, 152, 170)

FONT = M.FONT
FONT_B = M.FONT_B


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def gradient(w, h, c1, c2, vertical=True):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for i in range(h if vertical else w):
        t = i / max(1, (h if vertical else w) - 1)
        c = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        if vertical:
            d.line([(0, i), (w, i)], fill=c)
        else:
            d.line([(i, 0), (i, h)], fill=c)
    return img


def check(d, x, y, r=17):
    d.ellipse([x, y, x + 2 * r, y + 2 * r], outline=ACCENT, width=3)
    d.line([(x + r * 0.5, y + r), (x + r * 0.85, y + r * 1.45),
            (x + r * 1.55, y + r * 0.55)], fill=ACCENT, width=4, joint="curve")


def phone_screen():
    """Рендерим экран бота в 1080×1350 и закругляем."""
    src = "shots/2_catalog.png"
    if not os.path.exists(src):
        raise SystemExit("сначала запусти make_shots.py")
    im = Image.open(src).convert("RGB")
    im = im.resize((660, 825), Image.LANCZOS)
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], 34, fill=255)
    return im, mask


def cover():
    img = gradient(W, H, BG1, BG2)
    d = ImageDraw.Draw(img)

    # мягкое свечение
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([820, 120, 1720, 1020], fill=(14, 48, 66))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    img = Image.blend(img, Image.blend(img, glow, 0.55), 0.85)
    d = ImageDraw.Draw(img)

    # шапка
    d.text((92, 96), "ШВЕЙНЫЕ ЦЕХА · ТРИКОТАЖ · СПЕЦОДЕЖДА", font=font(24), fill=ACCENT)

    # заголовок
    d.text((92, 168), "Бот приёма", font=font(88, True), fill=WHITE)
    d.text((92, 268), "заказов", font=font(88, True), fill=ACCENT)
    d.text((92, 386), "для швейного цеха", font=font(46), fill=MUTED)

    # буллеты
    items = [
        "Клиент сам считает цену и срок",
        "Заявка приходит в Telegram с номером",
        "Каталог тканей, скидки, статусы",
        "Запуск за 3–5 дней, ваш отдельный бот",
    ]
    y = 500
    for it in items:
        check(d, 94, y + 6)
        d.text((148, y), it, font=font(34), fill=WHITE)
        y += 68

    # плашка с ценой
    price = "от 5 000 ₽ · настройка под ваш прайс"
    pf = font(32, True)
    pw = pf.getlength(price) + 64
    d.rounded_rectangle([92, 812, 92 + pw, 906], radius=24, fill=(18, 74, 100),
                        outline=ACCENT, width=2)
    d.text((124, 838), price, font=pf, fill=WHITE)

    d.text((92, 976), "Все вопросы задавайте в чат", font=font(34, True), fill=ACCENT)

    # телефон
    scr, mask = phone_screen()
    px, py = 900, 200
    shadow = Image.new("RGB", (W, H), (0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([px + 14, py + 26, px + 660 + 14, py + 825 + 26], 40, fill=(0, 0, 0))
    shadow = shadow.filter(ImageFilter.GaussianBlur(34))
    img = Image.composite(shadow, img, shadow.convert("L").point(lambda v: min(255, v * 2)))
    img.paste(scr, (px, py), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([px, py, px + 660, py + 825], radius=34, outline=(54, 84, 106), width=3)

    os.makedirs("shots", exist_ok=True)
    img.save("shots/0_cover.png", "PNG", optimize=True)
    print("готово: shots/0_cover.png", img.size)


def logo():
    s = 800
    img = Image.new("RGB", (s, s), (14, 26, 36))
    d = ImageDraw.Draw(img)
    for i in range(s):
        t = i / s
        d.line([(0, i), (s, i)], fill=tuple(int((14, 26, 36)[k] + ((26, 48, 64)[k] - (14, 26, 36)[k]) * t) for k in range(3)))
    d.rounded_rectangle([40, 40, s - 40, s - 40], radius=96, outline=(40, 78, 100), width=4)
    f1, f2 = font(200, True), font(56)
    d.text((s // 2 - f1.getlength("ЦЕХ") / 2, 210), "ЦЕХ", font=f1, fill=WHITE)
    d.text((s // 2 - f2.getlength("в Telegram") / 2, 560), "в Telegram", font=f2, fill=ACCENT)
    d.rounded_rectangle([s // 2 - 80, 660, s // 2 + 80, 668], radius=4, fill=ACCENT)
    os.makedirs("shots", exist_ok=True)
    img.save("shots/9_logo.png", "PNG", optimize=True)
    print("готово: shots/9_logo.png", img.size)


if __name__ == "__main__":
    cover()
    logo()
