# -*- coding: utf-8 -*-
"""
make_shots.py — рисует скриншоты бота для объявления на Avito.
Запуск: python make_shots.py
Результат: shots/1_menu.png … shots/8_collage.png
Название цеха берётся из config.py (SHOP["name"]).
"""

import os

from PIL import Image, ImageDraw, ImageFont

from config import SHOP

NAME = SHOP["name"]
W, H = 1080, 1350
PAD = 44

BG = (23, 33, 43)
HDR = (15, 23, 30)
BOT = (28, 42, 53)
USR = (43, 82, 120)
TXT = (233, 240, 246)
MUTED = (138, 154, 170)
BTN = (37, 55, 70)
ACCENT = (86, 156, 214)

FONT = "C:/Windows/Fonts/segoeui.ttf"
FONT_B = "C:/Windows/Fonts/segoeuib.ttf"

OUT = "shots"


def f(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def wrap(text, font, maxw):
    out, line = [], ""
    for word in text.split():
        probe = (line + " " + word).strip()
        if font.getlength(probe) <= maxw:
            line = probe
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out


def rr(d, box, r, fill=None, outline=None, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


class Chat:
    def __init__(self, title, subtitle):
        self.img = Image.new("RGB", (W, H), BG)
        self.d = ImageDraw.Draw(self.img)
        self.y = 132
        self.d.rectangle([0, 0, W, 112], fill=HDR)
        self.d.text((PAD, 26), title, font=f(40, True), fill=TXT)
        self.d.text((PAD, 74), subtitle, font=f(24), fill=MUTED)
        self.d.line([0, 112, W, 112], fill=(38, 50, 62), width=2)

    def bubble(self, text, user=False, size=30):
        font = f(size)
        maxw = int(W * 0.72)
        lines = []
        for para in text.split("\n"):
            if not para.strip():
                lines.append("")
                continue
            lines.extend(wrap(para, font, maxw))
        lh = int(size * 1.42)
        bw = max((font.getlength(l) for l in lines if set(l) != {"─"}), default=0) + 56
        bw = min(bw, maxw + 56)
        bh = lh * len(lines) + 40
        x = W - PAD - bw if user else PAD
        rr(self.d, [x, self.y, x + bw, self.y + bh], 26, fill=USR if user else BOT)
        ty = self.y + 20
        for l in lines:
            if l and set(l) == {"─"}:
                self.d.line([x + 28, ty + lh // 2, x + bw - 28, ty + lh // 2],
                            fill=(70, 90, 108), width=2)
            elif l:
                self.d.text((x + 28, ty), l, font=font, fill=TXT)
            ty += lh
        self.y += bh + 16

    def buttons(self, rows, size=28):
        font = f(size)
        for row in rows:
            n = len(row)
            total = W - 2 * PAD
            gap = 12
            bw = (total - gap * (n - 1)) // n
            bh = 76
            x = PAD
            for label in row:
                rr(self.d, [x, self.y, x + bw, self.y + bh], 18, fill=BTN,
                   outline=(52, 76, 96), width=2)
                tw = font.getlength(label)
                self.d.text((x + (bw - tw) / 2, self.y + (bh - 38) / 2), label,
                            font=font, fill=ACCENT)
                x += bw + gap
            self.y += bh + 10
        self.y += 10

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, name)
        self.img.save(path, "PNG", optimize=True)
        print("готово:", path, self.img.size)


def shot_menu():
    c = Chat(NAME, "бот  ·  онлайн")
    c.bubble("Здравствуйте! Нужно отшить партию.", user=True)
    c.bubble(
        "Своё производство. Считаем заказ прямо в чате:\n"
        "• каталог тканей с ценами и наличием\n"
        "• расчёт стоимости и срока за 30 секунд\n"
        "• заявка с номером, принимаем от 10 шт"
    )
    c.buttons([["Каталог тканей"], ["Рассчитать заказ"], ["Оставить заявку"],
               ["Мои заявки"], ["Прайс", "Доставка"], ["Контакты"]])
    c.save("1_menu.png")


def shot_catalog():
    c = Chat(NAME, "бот  ·  онлайн")
    c.bubble("Каталог тканей", user=True)
    c.bubble(
        "Ткани · страница 1 из 3\n\n"
        "Нажмите на ткань — сразу перейдём к расчёту.\n\n"
        "• Кулирка 160 г/м² — 350 ₽/м  (в наличии)\n"
        "• Футер 2-нитка 280 г/м² — 650 ₽/м  (в наличии)\n"
        "• Интерлок 190 г/м² — 450 ₽/м  (в наличии)\n"
        "• Поплин 110 г/м² — 380 ₽/м  (в наличии)"
    )
    c.buttons([["Кулирка 160 г/м² · 350 ₽/м"],
               ["Футер 2-нитка 280 г/м² · 650 ₽/м"],
               ["Интерлок 190 г/м² · 450 ₽/м"],
               ["Поплин 110 г/м² · 380 ₽/м"],
               ["<", "1 / 3", ">"],
               ["В меню"]])
    c.save("2_catalog.png")


def shot_result():
    c = Chat(NAME, "бот  ·  онлайн")
    c.bubble("Худи, 100 штук, футер, печать DTF", user=True)
    c.bubble(
        "Расчёт заказа\n\n"
        "Изделие: Худи\n"
        "Ткань: Футер 2-нитка 280 г/м²\n"
        "Тираж: 100 шт\n\n"
        "Ткань (180 м): 117 000 ₽\n"
        "Пошив: 90 000 ₽\n"
        "Опции (Печать DTF): 15 000 ₽\n"
        "Скидка 5%: −11 100 ₽\n"
        "───────────\n"
        "Итого: 210 900 ₽\n"
        "≈ 2 109 ₽ за штуку\n"
        "Срок: 14–18 дней"
    )
    c.buttons([["Оформить заявку"], ["Пересчитать"], ["В меню"]])
    c.save("3_calc.png")


def shot_price():
    c = Chat(NAME, "бот  ·  онлайн")
    c.bubble("Прайс", user=True)
    c.bubble(
        "Прайс пошива (за 1 шт., ткань отдельно)\n\n"
        "• Футболка — 450 ₽\n"
        "• Лонгслив — 550 ₽\n"
        "• Худи — 900 ₽\n"
        "• Платье — 1 200 ₽\n"
        "• Костюм спортивный — 1 000 ₽\n"
        "• Штаны — 850 ₽\n"
        "• Шорты — 500 ₽\n"
        "• Рубашка — 1 100 ₽\n\n"
        "Опции\n"
        "• Печать DTF — +150 ₽/шт\n"
        "• Вышивка лого — +250 ₽/шт\n"
        "• Упаковка — +30 ₽/шт\n\n"
        "Скидка от тиража\n"
        "• 0–49 шт — 0%\n"
        "• 50–99 шт — 3%\n"
        "• 100–299 шт — 5%\n"
        "• от 300 шт — 7%\n\n"
        "Минимальный тираж — 10 шт."
    )
    c.buttons([["В меню"]])
    c.save("4_price.png")


def shot_manager():
    c = Chat("Менеджер", "личные сообщения")
    c.bubble(
        "Новая заявка\n\n"
        "Заказ ШВ-0014\n"
        "Изделие: Худи\n"
        "Ткань: Футер 2-нитка 280 г/м²\n"
        "Тираж: 125 шт\n"
        "Опции: Печать DTF\n"
        "Итого: 269 562 ₽\n"
        "Срок: 14–18 дней\n\n"
        "Клиент: Иван\n"
        "Телефон: +7 900 123-45-67\n"
        "TG: @ivan"
    )
    c.save("5_manager.png")


def shot_admin():
    c = Chat("Менеджер", "админка бота")
    c.bubble("Заявки", user=True)
    c.bubble(
        "ШВ-0014  ·  10.11.2026 20:52\n\n"
        "Клиент: Иван\n"
        "Телефон: +7 900 123-45-67\n"
        "Изделие: Худи\n"
        "Ткань: Футер 2-нитка 280 г/м²\n"
        "Тираж: 125 шт\n"
        "Опции: Печать DTF\n"
        "Итого: 269 562 ₽\n"
        "Статус: новая"
    )
    c.buttons([["В работу", "Выполнен"], ["Отменить"], ["<", ">"]])
    c.save("6_admin.png")


def shot_my():
    c = Chat(NAME, "бот  ·  онлайн")
    c.bubble("Мои заявки", user=True)
    c.bubble(
        "Ваши заявки\n\n"
        "• ШВ-0014 · Худи · 125 шт · 269 562 ₽\n"
        "   10.11.2026 20:52 · в работе\n\n"
        "• ШВ-0011 · Футболка · 50 шт · 47 500 ₽\n"
        "   03.11.2026 · выполнен\n\n"
        "• ШВ-0009 · Шорты · 300 шт · 148 200 ₽\n"
        "   28.10.2026 · выполнен"
    )
    c.buttons([["Рассчитать заказ"], ["В меню"]])
    c.save("7_my.png")


def shot_collage():
    files = ["1_menu.png", "2_catalog.png", "3_calc.png", "4_price.png"]
    imgs = [Image.open(os.path.join(OUT, n)) for n in files]
    tw, th = 540, 675
    canvas = Image.new("RGB", (tw * 2, th * 2), BG)
    for i, im in enumerate(imgs):
        canvas.paste(im.resize((tw, th), Image.LANCZOS), ((i % 2) * tw, (i // 2) * th))
    canvas.save(os.path.join(OUT, "8_collage.png"), "PNG", optimize=True)
    print("готово: shots/8_collage.png", canvas.size)


if __name__ == "__main__":
    shot_menu()
    shot_catalog()
    shot_result()
    shot_price()
    shot_manager()
    shot_admin()
    shot_my()
    shot_collage()
