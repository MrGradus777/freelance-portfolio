"""Telegram-бот приёма заявок.

Сценарий:
    /start -> пошаговая форма (имя, телефон, описание задачи) -> подтверждение
    -> заявка сохраняется в SQLite и отправляется администратору в Telegram.

Запуск:
    cp .env.example .env   # вписать BOT_TOKEN и ADMIN_ID
    pip install -r requirements.txt
    python bot.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
DB_PATH = os.getenv("DB_PATH", "orders.db")

PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{9,17}$")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

dp = Dispatcher()


class OrderForm(StatesGroup):
    """Шаги формы заявки."""

    name = State()
    phone = State()
    task = State()
    confirm = State()


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                username    TEXT,
                name        TEXT NOT NULL,
                phone       TEXT NOT NULL,
                task        TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'new',
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_order(user_id: int, username: str | None, name: str, phone: str, task: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO orders (user_id, username, name, phone, task, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, name, phone, task, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return int(cur.lastrowid)


def orders_count() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
    return int(row[0]) if row else 0


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(OrderForm.name)
    await message.answer(
        "Здравствуйте! Оставьте заявку — я свяжусь с вами в течение дня.\n\n"
        "Как вас зовут?"
    )


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Заявка отменена. Если понадобится — /start", reply_markup=ReplyKeyboardRemove())


@dp.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Простая админ-команда: сколько заявок в базе."""
    if message.from_user and message.from_user.id == ADMIN_ID:
        await message.answer(f"Заявок в базе: {orders_count()}")


@dp.message(OrderForm.name, F.text)
async def step_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Напишите, пожалуйста, ещё раз.")
        return
    await state.update_data(name=name)
    await state.set_state(OrderForm.phone)
    await message.answer(
        "Как с вами связаться? Телефон в формате +7 900 000-00-00 "
        "или нажмите кнопку ниже.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отправить мой номер", request_contact=True)]],
            resize_keyboard=True,
        ),
    )


@dp.message(OrderForm.phone, F.contact)
async def step_phone_contact(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number if message.contact else ""
    await _accept_phone(message, state, phone)


@dp.message(OrderForm.phone, F.text)
async def step_phone_text(message: Message, state: FSMContext) -> None:
    await _accept_phone(message, state, (message.text or "").strip())


async def _accept_phone(message: Message, state: FSMContext, phone: str) -> None:
    if not PHONE_RE.match(phone.replace(" ", "")):
        await message.answer("Не похоже на номер. Пример: +7 900 000-00-00")
        return
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.task)
    await message.answer("Опишите задачу в двух-трёх предложениях.", reply_markup=ReplyKeyboardRemove())


@dp.message(OrderForm.task, F.text)
async def step_task(message: Message, state: FSMContext) -> None:
    task = (message.text or "").strip()
    if len(task) < 10:
        await message.answer("Добавьте деталей — хотя бы пару предложений.")
        return
    data = await state.get_data()
    await state.update_data(task=task)
    await state.set_state(OrderForm.confirm)
    await message.answer(
        "Проверьте заявку:\n\n"
        f"Имя: {data.get('name')}\n"
        f"Телефон: {data.get('phone')}\n"
        f"Задача: {task}\n\n"
        "Всё верно?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отправить"), KeyboardButton(text="Отмена")]],
            resize_keyboard=True,
        ),
    )


@dp.message(OrderForm.confirm, F.text)
async def step_confirm(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip().lower() in {"отмена", "cancel"}:
        await state.clear()
        await message.answer("Хорошо, отменил.", reply_markup=ReplyKeyboardRemove())
        return

    data = await state.get_data()
    order_id = save_order(
        user_id=message.from_user.id if message.from_user else 0,
        username=message.from_user.username if message.from_user else None,
        name=str(data.get("name", "")),
        phone=str(data.get("phone", "")),
        task=str(data.get("task", "")),
    )
    await state.clear()
    await message.answer(
        f"Спасибо! Заявка №{order_id} принята — свяжусь с вами в течение дня.",
        reply_markup=ReplyKeyboardRemove(),
    )

    admin_text = (
        f"Новая заявка №{order_id}\n\n"
        f"Имя: {data.get('name')}\n"
        f"Телефон: {data.get('phone')}\n"
        f"Задача: {data.get('task')}\n"
        f"Пользователь: @{message.from_user.username or 'без ника'} "
        f"(id {message.from_user.id if message.from_user else '—'})"
    )
    if ADMIN_ID:
        try:
            await message.bot.send_message(ADMIN_ID, admin_text)
        except Exception as exc:  # noqa: BLE001 — админ мог не начать чат с ботом
            log.warning("Не удалось отправить уведомление админу: %s", exc)


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN не задан. Скопируйте .env.example в .env и впишите токен.")
    init_db()
    bot = Bot(token=BOT_TOKEN)
    log.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
