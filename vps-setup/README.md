# vps-setup — развёртывание бота на сервере

Инструкция и скрипты, чтобы бот не «умер» после закрытия ноутбука: VPS, Docker,
автозапуск, логи с ротацией и ежедневные бэкапы.

## Что внутри

| Файл | Назначение |
|---|---|
| [`deploy.md`](deploy.md) | пошагово: сервер → защита → Docker → запуск → бэкапы → обновление |
| [`backup.sh`](backup.sh) | архив папки `data` + ротация архивов старше 14 дней |

## Быстрый старт

```bash
# на сервере
git clone https://github.com/MrGradus777/freelance-portfolio.git /opt/orders-bot
cd /opt/orders-bot/bot-orders
cp .env.example .env && nano .env
docker compose up -d --build

# ежедневный бэкап
chmod +x /opt/orders-bot/vps-setup/backup.sh
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/orders-bot/vps-setup/backup.sh >> /var/log/orders-backup.log 2>&1") | crontab -
```

## Что получает заказчик

- Бот работает 24/7 и поднимается сам после перезагрузки сервера.
- Данные не теряются: ежедневный архив, старые копии удаляются автоматически.
- Понятный регламент обновления — без простоя и без «а что тут было настроено».

## Минимальный сервер

1 vCPU, 1 ГБ RAM, 10 ГБ SSD (Ubuntu 22.04/24.04) — хватает для бота с базой
и запасом. Стоимость от ~200 ₽/мес.
