#!/usr/bin/env bash
# Бэкап данных бота: архив папки data + ротация старых архивов.
# Запуск вручную:      ./backup.sh
# Запуск по cron:      0 3 * * * /opt/orders-bot/vps-setup/backup.sh >> /var/log/orders-backup.log 2>&1
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/orders-bot}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/orders-bot}"
KEEP_DAYS="${KEEP_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%F_%H%M)"
ARCHIVE="$BACKUP_DIR/data_$STAMP.tar.gz"

tar -czf "$ARCHIVE" -C "$APP_DIR" data
find "$BACKUP_DIR" -name 'data_*.tar.gz' -mtime +"$KEEP_DAYS" -delete

echo "backup ok: $ARCHIVE"
