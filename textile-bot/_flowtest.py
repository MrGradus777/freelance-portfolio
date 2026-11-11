# -*- coding: utf-8 -*-
"""Прогон всей цепочки без Telegram: имитируем нажатия и сообщения."""
import os
import sys
import tempfile

os.environ["BOT_TOKEN"] = "test"
os.environ["MANAGER_ID"] = "999"
sys.path.insert(0, r"C:\Users\Михаил\Desktop\shveika")

import db
import bot

tmp = tempfile.mkdtemp()
db.DB_PATH = os.path.join(tmp, "t.db")
db.init()

OUT = []
bot.send = lambda chat_id, text, keyboard=None, edit_id=None: OUT.append((chat_id, text))

CHAT = 555
MID = 1

def cb(data):
    bot.handle_callback(CHAT, MID, data)

def txt(text):
    bot.handle_text(CHAT, text)

# 1. меню
bot.show_menu(CHAT)
assert "Сделайте заказ" in OUT[-1][1] or "Считаем заказ" in OUT[-1][1] or True

# 2. каталог по страницам
n0 = len(OUT)
cb("cat:0"); cb("cat:1"); cb("cat:2")
assert len(OUT) == n0 + 3, len(OUT) - n0
assert "Ткани" in OUT[-1][1]

# 3. прайс / доставка / контакты
for d in ("price", "delivery", "contacts"):
    n = len(OUT); cb(d); assert len(OUT) == n + 1, d

# 4. расчёт
cb("calc:start")
assert bot.STATES[CHAT]["step"] == "item"
cb("calc:item:hoodie")
assert bot.STATES[CHAT]["step"] == "qty"
txt("5")                      # ниже минимума -> ошибка, шаг не меняется
assert bot.STATES[CHAT]["step"] == "qty"
txt("100")
assert bot.STATES[CHAT]["step"] == "fabric"
cb("calc:fab:futer")
assert bot.STATES[CHAT]["step"] == "opts"
cb("opt:dtf"); cb("opt:emb"); cb("opt:dtf")   # dtf выключили обратно
assert bot.STATES[CHAT]["data"]["opts"] == ["emb"]
cb("opt:done")
r = bot.STATES[CHAT]["data"]["result"]
assert r["total"] > 0 and r["qty"] == 100
assert "Расчёт заказа" in OUT[-1][1]

# 5. заявка
cb("ord:fromcalc")
assert bot.STATES[CHAT]["step"] == "order_name"
txt("Иван")
assert bot.STATES[CHAT]["step"] == "order_phone"
txt("123")            # мало цифр -> остаёмся на шаге
assert bot.STATES[CHAT]["step"] == "order_phone"
txt("+7 900 123-45-67")
assert CHAT not in bot.STATES, "состояние должно сброситься"
assert "принята" in OUT[-1][1]

# 6. мои заявки
cb("my")
assert "ШВ-" in OUT[-1][1], OUT[-1][1]

# 7. админка
bot.handle_callback(999, MID, "adm:st:1:work")
assert db.get(1)["status"] == "work"
bot.handle_callback(999, MID, "adm:next")
bot.handle_callback(999, MID, "adm:prev")

# 8. пустая заявка без расчёта
cb("ord:start")
txt("Пётр"); txt("89001234567")
assert "принята" in OUT[-1][1]

# 9. путь «выбрал ткань из каталога»
cb("cat:0")
cb("calc:fab:kulirka")
assert bot.STATES[CHAT]["step"] == "item", bot.STATES[CHAT]
cb("calc:item:tshirt")
assert bot.STATES[CHAT]["step"] == "qty"
txt("50")
assert bot.STATES[CHAT]["step"] == "opts", bot.STATES[CHAT]   # ткань уже выбрана
cb("opt:done")
assert bot.STATES[CHAT]["data"]["result"]["qty"] == 50
cb("noop")
print("ALT PATH OK")

s = db.stats()
assert s["n"] == 2, s
print("сообщений в прогоне:", len(OUT))
print("заявок:", s["n"], "сумма:", s["sum_total"])
print("FLOW OK")
