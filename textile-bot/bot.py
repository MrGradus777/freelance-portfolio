#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot.py — «Цех в Telegram»: каталог, расчёт заказа, заявки, админка.

Запуск:
    $env:BOT_TOKEN="123:AA..."
    $env:MANAGER_ID="123456789"
    python bot.py

Проверка без Telegram:
    python bot.py --selftest
"""

import html
import json
import os
import sys
import time
import urllib.error
import urllib.request

import config as C
import db

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
MANAGER_ID = os.environ.get("MANAGER_ID", "").strip()

# ──────────────────────────── Telegram API ────────────────────────────


def api(method, **params):
    url = "https://api.telegram.org/bot%s/%s" % (TOKEN, method)
    req = urllib.request.Request(
        url,
        data=json.dumps(params).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def send(chat_id, text, keyboard=None, edit_id=None):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if keyboard is not None:
        params["reply_markup"] = {"inline_keyboard": keyboard}
    if edit_id:
        params["message_id"] = edit_id
        try:
            return api("editMessageText", **params)
        except urllib.error.HTTPError as e:
            body = e.read() or b""
            if e.code == 400 and b"not modified" in body:
                return None
            raise
    return api("sendMessage", **params)


def ack(cb_id):
    try:
        api("answerCallbackQuery", callback_query_id=cb_id)
    except Exception:
        pass


def note_chat(chat_id, username=""):
    """Запоминает последний чат — чтобы при настройке узнать MANAGER_ID."""
    try:
        os.makedirs(os.path.join(os.path.dirname(db.DB_PATH)), exist_ok=True)
        with open(os.path.join(os.path.dirname(db.DB_PATH), "last_chat.txt"), "w",
                  encoding="utf-8") as f:
            f.write("%s %s\n" % (chat_id, username or ""))
    except Exception:
        pass


# ──────────────────────────── расчёт ────────────────────────────


def money(v):
    return "{:,}".format(int(round(v))).replace(",", " ") + " ₽"


def find(seq, code):
    return next((x for x in seq if x["code"] == code), None)


def discount_for(qty):
    for lo, hi, pct in C.DISCOUNTS:
        if lo <= qty <= hi:
            return pct
    return 0


def turnaround_for(qty):
    for lo, hi, label in C.TURNAROUND:
        if lo <= qty <= hi:
            return label
    return "уточняется"


def calc(item_code, fabric_code, qty, opt_codes=()):
    item, fabric = find(C.ITEMS, item_code), find(C.FABRICS, fabric_code)
    if not item or not fabric:
        return None
    fabric_cost = round(fabric["price"] * item["need"] * qty)
    sew_cost = item["sew"] * qty
    opt_list = [o for o in C.OPTIONS if o["code"] in opt_codes]
    opt_cost = sum(o["price"] for o in opt_list) * qty
    gross = fabric_cost + sew_cost + opt_cost
    pct = discount_for(qty)
    discount = round(gross * pct / 100)
    total = gross - discount
    return {
        "item": item, "fabric": fabric, "qty": qty,
        "fabric_cost": fabric_cost, "sew_cost": sew_cost,
        "opt_cost": opt_cost, "opt_list": opt_list,
        "gross": gross, "pct": pct, "discount": discount,
        "total": total,
        "per_unit": round(total / qty) if qty else 0,
        "days": turnaround_for(qty),
        "meters": round(item["need"] * qty, 1),
    }


# ──────────────────────────── клавиатуры ────────────────────────────


def kb_main():
    return [
        [{"text": "🧵 Каталог тканей", "callback_data": "cat:0"}],
        [{"text": "🧮 Рассчитать заказ", "callback_data": "calc:start"}],
        [{"text": "✍️ Оставить заявку", "callback_data": "ord:start"},
         {"text": "📦 Мои заявки", "callback_data": "my"}],
        [{"text": "💰 Прайс", "callback_data": "price"},
         {"text": "🚚 Доставка", "callback_data": "delivery"}],
        [{"text": "📞 Контакты", "callback_data": "contacts"}],
    ]


def kb_back():
    return [[{"text": "🏠 В меню", "callback_data": "menu"}]]


def kb_items():
    rows = [[{"text": i["name"], "callback_data": "calc:item:" + i["code"]}] for i in C.ITEMS]
    rows.append([{"text": "🏠 В меню", "callback_data": "menu"}])
    return rows


def kb_fabrics():
    rows = [
        [{"text": "%s — %s ₽/м" % (f["name"], f["price"]),
          "callback_data": "calc:fab:" + f["code"]}]
        for f in C.FABRICS
    ]
    rows.append([{"text": "🏠 В меню", "callback_data": "menu"}])
    return rows


def kb_options(chosen):
    rows = []
    for o in C.OPTIONS:
        mark = "✅ " if o["code"] in chosen else ""
        rows.append([{"text": "%s%s — %s/шт" % (mark, o["name"], o["price"]),
                      "callback_data": "opt:" + o["code"]}])
    rows.append([{"text": "➡️ Посчитать", "callback_data": "opt:done"}])
    rows.append([{"text": "🏠 В меню", "callback_data": "menu"}])
    return rows


def kb_result():
    return [
        [{"text": "✍️ Оформить заявку", "callback_data": "ord:fromcalc"}],
        [{"text": "🔄 Пересчитать", "callback_data": "calc:start"}],
        [{"text": "🏠 В меню", "callback_data": "menu"}],
    ]


# ──────────────────────────── состояние ────────────────────────────

STATES = {}      # chat_id -> {"step": str, "data": dict}
ADMIN_IDX = {}   # chat_id -> индекс в списке заявок
USERNAMES = {}   # chat_id -> @username


def reset(chat_id):
    STATES.pop(chat_id, None)


def menu_text():
    return C.WELCOME.format(shop=html.escape(C.SHOP["name"]), min_qty=C.MIN_QTY)


def show_menu(chat_id, edit_id=None):
    reset(chat_id)
    send(chat_id, menu_text(), kb_main(), edit_id)


def step_no(d):
    return 1 + sum(1 for k in ("item", "qty", "fabric") if k in d)


def advance(chat_id, msg_id=None):
    """Единая точка: спрашиваем только то, чего ещё нет в заказе."""
    st = STATES.setdefault(chat_id, {"step": "item", "data": {"opts": []}})
    d = st["data"]
    d.setdefault("opts", [])
    if "item" not in d:
        st["step"] = "item"
        send(chat_id, "Шаг %d/4. Что шьём?" % step_no(d), kb_items(), msg_id)
    elif "qty" not in d:
        st["step"] = "qty"
        send(chat_id, "Шаг %d/4. Сколько штук? Минимум %d, например: <code>100</code>"
             % (step_no(d), C.MIN_QTY), kb_back(), msg_id)
    elif "fabric" not in d:
        st["step"] = "fabric"
        send(chat_id, "Шаг %d/4. Из какой ткани шьём?" % step_no(d), kb_fabrics(), msg_id)
    else:
        st["step"] = "opts"
        send(chat_id, "Шаг %d/4. Дополнительные опции (можно несколько):" % step_no(d),
             kb_options(d["opts"]), msg_id)


# ──────────────────────────── экраны ────────────────────────────


def screen_catalog(chat_id, msg_id, page):
    per = 4
    pages = max(1, (len(C.FABRICS) + per - 1) // per)
    page = max(0, min(page, pages - 1))
    chunk = C.FABRICS[page * per:(page + 1) * per]
    lines = ["<b>Ткани</b> · страница %d из %d\n" % (page + 1, pages),
             "Нажмите на ткань — сразу перейдём к расчёту.\n"]
    for f in chunk:
        lines.append("• <b>%s</b> — %s ₽/м <i>(%s)</i>" % (f["name"], f["price"], f["stock"]))
    kb = [[{"text": "%s · %s ₽/м" % (f["name"], f["price"]),
            "callback_data": "calc:fab:" + f["code"]}] for f in chunk]
    kb.append([
        {"text": "◀️" if page > 0 else "·",
         "callback_data": "cat:%d" % (page - 1) if page > 0 else "noop"},
        {"text": "%d / %d" % (page + 1, pages), "callback_data": "noop"},
        {"text": "▶️" if page + 1 < pages else "·",
         "callback_data": "cat:%d" % (page + 1) if page + 1 < pages else "noop"},
    ])
    kb.append([{"text": "🏠 В меню", "callback_data": "menu"}])
    send(chat_id, "\n".join(lines), kb, msg_id)


def screen_price(chat_id, msg_id):
    lines = ["<b>Прайс пошива</b> (цена за 1 шт., ткань считается отдельно)\n"]
    for i in C.ITEMS:
        lines.append("• %s — %s" % (i["name"], money(i["sew"])))
    lines.append("\n<b>Опции</b>")
    for o in C.OPTIONS:
        lines.append("• %s — +%s/шт" % (o["name"], money(o["price"])))
    lines.append("\n<b>Скидка от тиража</b>")
    for lo, hi, pct in C.DISCOUNTS:
        rng = "от %d шт" % lo if hi >= 10 ** 9 else "%d–%d шт" % (lo, hi)
        lines.append("• %s — %d%%" % (rng, pct))
    lines.append("\nМинимальный тираж — %d шт." % C.MIN_QTY)
    send(chat_id, "\n".join(lines), kb_back(), msg_id)


def screen_delivery(chat_id, msg_id):
    send(
        chat_id,
        "<b>Сроки и доставка</b>\n\n"
        + "\n".join("• %s" % d for d in [
            "Пошив — от 7 рабочих дней, точнее считается в заказе",
            "Доставка: " + C.SHOP["delivery"],
            "Самовывоз: " + C.SHOP["address"],
            "Работаем с Wildberries и Ozon, отшиваем под их требования",
        ]),
        kb_back(), msg_id,
    )


def screen_contacts(chat_id, msg_id):
    s = C.SHOP
    send(
        chat_id,
        "<b>Контакты</b>\n\n"
        "Телефон: <b>%s</b>\nАдрес: %s\nЧасы: %s\n\n%s"
        % (html.escape(s["phone"]), html.escape(s["address"]),
           html.escape(s["hours"]), html.escape(s["about"])),
        kb_back(), msg_id,
    )


def screen_result(chat_id, msg_id, r):
    lines = [
        "<b>Расчёт заказа</b>\n",
        "Изделие: <b>%s</b>" % html.escape(r["item"]["name"]),
        "Ткань: %s" % html.escape(r["fabric"]["name"]),
        "Тираж: <b>%d шт</b>" % r["qty"],
        "",
        "Ткань (%s м): %s" % (r["meters"], money(r["fabric_cost"])),
        "Пошив: %s" % money(r["sew_cost"]),
    ]
    if r["opt_cost"]:
        names = ", ".join(html.escape(o["name"]) for o in r["opt_list"])
        lines.append("Опции (%s): %s" % (names, money(r["opt_cost"])))
    if r["discount"]:
        lines.append("Скидка %d%%: −%s" % (r["pct"], money(r["discount"])))
    lines += [
        "───────────",
        "<b>Итого: %s</b>" % money(r["total"]),
        "≈ %s за штуку" % money(r["per_unit"]),
        "Срок: <b>%s</b>" % r["days"],
    ]
    send(chat_id, "\n".join(lines), kb_result(), msg_id)


# ──────────────────────────── заявки ────────────────────────────


def notify_manager(order_id, num, tg_id, name, phone, r, comment=""):
    if not MANAGER_ID:
        return
    if r:
        body = (
            "<b>Заказ %s</b>\n"
            "Изделие: %s\nТкань: %s\nТираж: %d шт\n"
            "Опции: %s\nИтого: <b>%s</b>\nСрок: %s"
            % (
                num, html.escape(r["item"]["name"]), html.escape(r["fabric"]["name"]),
                r["qty"],
                html.escape(", ".join(o["name"] for o in r["opt_list"]) or "нет"),
                money(r["total"]), r["days"],
            )
        )
    else:
        body = "<b>Заказ %s</b>\nБез расчёта (клиент оставил заявку вручную)" % num
    send(
        MANAGER_ID,
        "🔔 <b>Новая заявка</b>\n\n"
        "%s\n\nКлиент: <b>%s</b>\nТелефон: <code>%s</code>\nTG: %s"
        % (body, html.escape(name), html.escape(phone),
           "@%s" % tg_id if tg_id else "—"),
    )


def screen_my(chat_id, msg_id):
    rows = db.by_client(chat_id)
    if not rows:
        send(chat_id, "Заявок пока нет.\n\nПосчитайте заказ и оформите — займёт минуту.",
             [[{"text": "🧮 Рассчитать", "callback_data": "calc:start"}],
              [{"text": "🏠 В меню", "callback_data": "menu"}]], msg_id)
        return
    lines = ["<b>Ваши заявки</b>\n"]
    for r in rows:
        lines.append(
            "• <b>ШВ-%04d</b> · %s · %d шт · %s\n   %s · %s"
            % (r["id"], html.escape(r["item"] or "—"), r["qty"] or 0,
               money(r["total"] or 0), r["created"],
               db.STATUS_LABEL.get(r["status"], r["status"]))
        )
    send(chat_id, "\n".join(lines), kb_back(), msg_id)


# ──────────────────────────── админка ────────────────────────────


def admin_show(chat_id, idx=0):
    rows = db.by_status("new", 20) + db.by_status("work", 20)
    if not rows:
        send(chat_id, "Активных заявок нет.", kb_back())
        return
    idx = max(0, min(idx, len(rows) - 1))
    ADMIN_IDX[chat_id] = idx
    r = rows[idx]
    text = (
        "<b>ШВ-%04d</b> · %s\n\n"
        "Клиент: %s\nТелефон: <code>%s</code>\n"
        "Изделие: %s\nТкань: %s\nТираж: %d шт\nОпции: %s\n"
        "Итого: <b>%s</b>\nСтатус: %s"
        % (
            r["id"], r["created"], html.escape(r["name"] or ""), html.escape(r["phone"] or ""),
            html.escape(r["item"] or "—"), html.escape(r["fabric"] or "—"), r["qty"] or 0,
            html.escape(r["options"] or "нет"), money(r["total"] or 0),
            db.STATUS_LABEL.get(r["status"], r["status"]),
        )
    )
    kb = [
        [{"text": "🔧 В работу", "callback_data": "adm:st:%d:work" % r["id"]},
         {"text": "✅ Выполнен", "callback_data": "adm:st:%d:done" % r["id"]}],
        [{"text": "❌ Отменить", "callback_data": "adm:st:%d:cancel" % r["id"]}],
        [{"text": "◀️", "callback_data": "adm:prev"}, {"text": "▶️", "callback_data": "adm:next"}],
    ]
    send(chat_id, text, kb)


# ──────────────────────────── коллбеки ────────────────────────────


def handle_callback(chat_id, msg_id, data):
    if data == "menu":
        show_menu(chat_id, msg_id)
        return

    if data.startswith("cat:"):
        screen_catalog(chat_id, msg_id, int(data.split(":", 1)[1]))
        return
    if data == "price":
        screen_price(chat_id, msg_id)
        return
    if data == "delivery":
        screen_delivery(chat_id, msg_id)
        return
    if data == "contacts":
        screen_contacts(chat_id, msg_id)
        return
    if data == "my":
        screen_my(chat_id, msg_id)
        return

    # ── калькулятор ──
    if data == "noop":
        return
    if data == "calc:start":
        STATES[chat_id] = {"step": "item", "data": {"opts": []}}
        advance(chat_id, msg_id)
        return
    if data.startswith("calc:item:"):
        st = STATES.setdefault(chat_id, {"step": "item", "data": {"opts": []}})
        st["data"]["item"] = data.split(":", 2)[2]
        advance(chat_id, msg_id)
        return
    if data.startswith("calc:fab:"):
        st = STATES.setdefault(chat_id, {"step": "fabric", "data": {"opts": []}})
        st["data"].setdefault("opts", [])
        st["data"]["fabric"] = data.split(":", 2)[2]
        advance(chat_id, msg_id)
        return
    if data.startswith("opt:"):
        st = STATES.get(chat_id)
        if not st:
            show_menu(chat_id, msg_id)
            return
        code = data.split(":", 1)[1]
        if code == "done":
            d = st["data"]
            r = calc(d.get("item"), d.get("fabric"), int(d.get("qty", 0)), d.get("opts", []))
            if not r:
                send(chat_id, "Что-то не сходится, начнём заново.", kb_back())
                return
            st["step"] = "result"
            st["data"]["result"] = r
            STATES[chat_id] = st
            screen_result(chat_id, msg_id, r)
            return
        opts = st["data"].setdefault("opts", [])
        if code in opts:
            opts.remove(code)
        else:
            opts.append(code)
        send(chat_id, "Шаг 4/4. Дополнительные опции:", kb_options(opts), msg_id)
        return

    # ── заявка ──
    if data == "ord:start":
        STATES[chat_id] = {"step": "order_name", "data": {"result": None}}
        send(chat_id, "Шаг 1/2. Как вас зовут?", kb_back(), msg_id)
        return
    if data == "ord:fromcalc":
        st = STATES.get(chat_id) or {"step": "result", "data": {}}
        st["step"] = "order_name"
        STATES[chat_id] = st
        send(chat_id, "Как вас зовут? Менеджер будет знать, кому звонить.", kb_back(), msg_id)
        return

    # ── админ ──
    if data.startswith("adm:"):
        if str(chat_id) != MANAGER_ID:
            send(chat_id, "Команда только для менеджера.")
            return
        parts = data.split(":")
        if parts[1] == "st":
            db.set_status(int(parts[2]), parts[3])
            admin_show(chat_id, ADMIN_IDX.get(chat_id, 0))
            return
        if parts[1] == "next":
            admin_show(chat_id, ADMIN_IDX.get(chat_id, 0) + 1)
            return
        if parts[1] == "prev":
            admin_show(chat_id, ADMIN_IDX.get(chat_id, 0) - 1)
            return


# ──────────────────────────── текст ────────────────────────────


def handle_text(chat_id, text):
    st = STATES.get(chat_id)
    if not st:
        show_menu(chat_id)
        return
    step = st["step"]

    if step == "qty":
        try:
            qty = int(text.strip())
            if not (C.MIN_QTY <= qty <= C.MAX_QTY):
                raise ValueError
        except ValueError:
            send(chat_id, "Нужно целое число от %d до %d, например: <code>100</code>"
                 % (C.MIN_QTY, C.MAX_QTY), kb_back())
            return
        st["data"]["qty"] = qty
        advance(chat_id)
        return

    if step == "order_name":
        name = text.strip()[:80]
        if len(name) < 2:
            send(chat_id, "Напишите имя, пожалуйста.", kb_back())
            return
        st["data"]["name"] = name
        st["step"] = "order_phone"
        send(chat_id, "Телефон для связи? Например: <code>+7 900 000-00-00</code>", kb_back())
        return

    if step == "order_phone":
        phone = text.strip()[:40]
        digits = sum(ch.isdigit() for ch in phone)
        if digits < 10:
            send(chat_id, "Похоже, в номере ошибка. Введите 10–11 цифр.", kb_back())
            return
        st["data"]["phone"] = phone
        d = st["data"]
        r = d.get("result")
        username = USERNAMES.get(chat_id, "")
        opts = ", ".join(o["name"] for o in r["opt_list"]) if r else ""
        order_id, num = db.add_order(
            chat_id, username, d.get("name", ""), phone,
            item=r["item"]["name"] if r else "—",
            fabric=r["fabric"]["name"] if r else "—",
            qty=r["qty"] if r else 0,
            options=opts or "нет",
            total=r["total"] if r else 0,
        )
        notify_manager(order_id, num, username, d.get("name", ""), phone, r)
        reset(chat_id)
        send(
            chat_id,
            "✅ <b>Заявка %s принята</b>\n\n"
            "Менеджер свяжется с вами в рабочее время.\n"
            "Мы уже видим ваш расчёт — обсуждать будем по делу.\n\n"
            "Номер можно посмотреть в «Мои заявки»." % num,
            kb_main(),
        )
        return

    show_menu(chat_id)


# ──────────────────────────── запуск ────────────────────────────


def main():
    if not TOKEN:
        print("Нет BOT_TOKEN. Заполните .env и запустите через start.bat.", file=sys.stderr)
        return 2
    db.init()
    print("Бот запущен. Ctrl+C — остановка.")
    offset, fails = 0, 0
    while True:
        try:
            updates = api("getUpdates", offset=offset, timeout=30,
                          allowed_updates=["message", "callback_query"]).get("result", [])
            fails = 0
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, e.read()[:200], file=sys.stderr)
            time.sleep(3)
            continue
        except Exception as e:
            fails += 1
            print("сеть:", e, file=sys.stderr)
            time.sleep(min(30, 2 * fails))
            continue

        for u in updates:
            offset = max(offset, u["update_id"] + 1)
            try:
                if "callback_query" in u:
                    cq = u["callback_query"]
                    ack(cq["id"])
                    handle_callback(cq["message"]["chat"]["id"],
                                    cq["message"]["message_id"], cq.get("data", ""))
                elif "message" in u:
                    m = u["message"]
                    chat_id = m["chat"]["id"]
                    note_chat(chat_id, (m.get("from") or {}).get("username", ""))
                    USERNAMES[chat_id] = (m.get("from") or {}).get("username", "")
                    text = (m.get("text") or "").strip()
                    if text in ("/start", "/menu"):
                        show_menu(chat_id)
                    elif text == "/admin":
                        if str(chat_id) == MANAGER_ID:
                            admin_show(chat_id, 0)
                        else:
                            send(chat_id, "Команда только для менеджера.")
                    elif text == "/whoami":
                        send(chat_id, "Ваш chat_id: <code>%d</code>" % chat_id)
                    elif text == "/stats":
                        if str(chat_id) == MANAGER_ID:
                            s = db.stats()
                            send(chat_id, "Всего заявок: %d\nНовых: %d\nСумма: %s"
                                 % (s["n"] or 0, s["n_new"] or 0, money(s["sum_total"] or 0)))
                        else:
                            send(chat_id, "Команда только для менеджера.")
                    elif text:
                        handle_text(chat_id, text)
                time.sleep(0.05)
            except Exception as e:
                print("ошибка обработки:", e, file=sys.stderr)
    return 0


def selftest():
    r = calc("hoodie", "futer", 50, ["dtf"])
    assert r, "расчёт не вернулся"
    fabric = round(650 * 1.8 * 50)
    sew = 900 * 50
    opt = 150 * 50
    gross = fabric + sew + opt
    disc = round(gross * 3 / 100)
    assert r["gross"] == gross, r["gross"]
    assert r["discount"] == disc, r["discount"]
    assert r["total"] == gross - disc
    assert r["days"] == "10–14 дней", r["days"]
    assert calc("hoodie", "nope", 10) is None
    assert discount_for(10) == 0 and discount_for(100) == 5 and discount_for(1000) == 7
    assert turnaround_for(10) == "7–10 дней" and turnaround_for(500) == "18–25 дней"
    for i in C.ITEMS:
        for f in C.FABRICS:
            rr = calc(i["code"], f["code"], 100)
            assert rr["total"] > 0 and rr["per_unit"] > 0
    print("config:", len(C.ITEMS), "изделий,", len(C.FABRICS), "тканей,", len(C.OPTIONS), "опций")
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(main())
