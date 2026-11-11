# bot-orders — Telegram-бот приёма заявок

Демо-проект: клиент заполняет форму в боте, заявка сохраняется в SQLite и уходит
администратору в Telegram. Основа для типового заказа «бот вместо потерянных заявок».

## Что умеет

- Пошаговая форма: имя → телефон (текстом или кнопкой «Отправить мой номер») → описание задачи → подтверждение.
- Валидация телефона и минимальной длины полей.
- Сохранение заявки в SQLite (без дублей и без внешних сервисов).
- Уведомление администратору в Telegram с номером заявки.
- Команды: `/start`, `/cancel`, `/stats` (только для админа).
- Контейнеризация: `Dockerfile` + `docker-compose.yml` с автоперезапуском.

## Структура

```
bot-orders/
├── bot.py               # весь сценарий бота
├── requirements.txt     # aiogram 3, python-dotenv
├── .env.example         # шаблон настроек
├── Dockerfile
└── docker-compose.yml
```

## Запуск локально

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env      # вписать BOT_TOKEN и ADMIN_ID
python bot.py
```

## Запуск в Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f --tail=50
```

## Что получает заказчик

- Заявки не теряются в личке и не уходят в спам.
- Все обращения в одной таблице, с датой и контактами.
- Админ узнаёт о заявке сразу, а не через день.

## Как адаптировать под заказ

1. Поля формы — в `OrderForm` и обработчиках `step_*`.
2. Таблица — в `init_db()`, при росте нагрузки заменить SQLite на PostgreSQL.
3. Уведомления — в `step_confirm` (можно добавить отправку в CRM или Google Sheets).
4. Тексты — строки в `message.answer()`, вынести в `messages.py` при расширении.
