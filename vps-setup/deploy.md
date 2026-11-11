# Развёртывание бота на VPS

Пошаговая инструкция: от чистого сервера до работающего бота с автозапуском и бэкапами.
Проверено на Ubuntu 22.04 / 24.04, подойдёт любой хостинг с root-доступом (Timeweb, Aeza, Selectel, Hetzner).

## 1. Что нужно

- VPS: 1 vCPU, 1 ГБ RAM, 10 ГБ SSD — хватает с запасом (от ~200 ₽/мес).
- Токен бота от [@BotFather](https://t.me/BotFather).
- Ваш Telegram ID (узнать: написать [@userinfobot](https://t.me/userinfobot)).

## 2. Первый вход и базовая защита

```bash
ssh root@IP_СЕРВЕРА

apt update && apt upgrade -y
adduser deploy && usermod -aG sudo deploy

# SSH-ключ для deploy (с локальной машины): ssh-copy-id deploy@IP_СЕРВЕРА
# После проверки входа по ключу отключаем пароль:
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh

# Файрвол: только SSH и ничего лишнего
ufw allow OpenSSH
ufw --force enable
```

## 3. Docker

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
# перелогиниться, чтобы группа применилась
```

## 4. Код и настройки

```bash
sudo mkdir -p /opt/orders-bot && sudo chown deploy:deploy /opt/orders-bot
git clone https://github.com/<username>/freelance-portfolio.git /opt/orders-bot
cd /opt/orders-bot/bot-orders

cp .env.example .env
nano .env    # BOT_TOKEN и ADMIN_ID
```

## 5. Запуск

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=50
```

Бот отвечает на `/start` — значит всё работает.

## 6. Автозапуск и живучесть

`restart: unless-stopped` в `docker-compose.yml` уже поднимает контейнер после ребута.
Проверка:

```bash
sudo reboot
# после перезагрузки:
docker compose ps   # снова Up
```

## 7. Бэкапы

```bash
sudo mkdir -p /var/backups/orders-bot
chmod +x /opt/orders-bot/vps-setup/backup.sh

# ежедневно в 03:00
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/orders-bot/vps-setup/backup.sh >> /var/log/orders-backup.log 2>&1") | crontab -
```

Раз в неделю скачивайте архив к себе:

```bash
scp deploy@IP_СЕРВЕРА:/var/backups/orders-bot/data_*.tar.gz ./
```

## 8. Обновление бота

```bash
cd /opt/orders-bot
git pull
cd bot-orders
docker compose up -d --build
```

## 9. Что смотреть при проблемах

| Симптом | Куда смотреть |
|---|---|
| Бот молчит | `docker compose logs --tail=100` |
| Контейнер перезапускается | ошибка в `.env` или неверный токен |
| Нет места на диске | `df -h`, почистить старые образы: `docker system prune -af` |
| Заявки не пишутся | права на папку `data`: `ls -la data` |

## 10. Безопасность

- `.env` не коммитить (он в `.gitignore`).
- Не запускать бота от root внутри контейнера — образ `python:3.12-slim` уже без лишних пакетов.
- Пароль по SSH отключён, доступ только по ключу и только по `ufw`.
