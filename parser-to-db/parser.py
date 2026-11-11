"""Парсер каталога в базу данных.

Что делает:
    1. Обходит страницы каталога (демо-источник: quotes.toscrape.com).
    2. Складывает записи в SQLite без дублей.
    3. Формирует отчёт: CSV-выгрузка + сводка по категориям в консоль.

Запуск:
    pip install -r requirements.txt
    python parser.py --pages 5
    python parser.py --pages 10 --out data/quotes.csv
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://quotes.toscrape.com"
DB_PATH = Path("data/catalog.db")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; portfolio-parser/1.0)"}


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                author      TEXT NOT NULL,
                tags        TEXT NOT NULL,
                source_url  TEXT NOT NULL,
                parsed_at   TEXT NOT NULL,
                UNIQUE (title, author)
            )
            """
        )
        conn.commit()


def fetch_page(page: int, timeout: int = 15) -> str:
    url = f"{BASE_URL}/page/{page}/"
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_page(html: str, page: int) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict[str, str]] = []
    for block in soup.select("div.quote"):
        text_el = block.select_one("span.text")
        author_el = block.select_one("small.author")
        tags = [tag.get_text(strip=True) for tag in block.select("a.tag")]
        if not text_el or not author_el:
            continue
        items.append(
            {
                "title": text_el.get_text(strip=True),
                "author": author_el.get_text(strip=True),
                "tags": ", ".join(tags),
                "source_url": f"{BASE_URL}/page/{page}/",
            }
        )
    return items


def save_items(db_path: Path, items: list[dict[str, str]]) -> tuple[int, int]:
    """Возвращает (добавлено, уже было)."""
    added = skipped = 0
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        for item in items:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO items (title, author, tags, source_url, parsed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item["title"], item["author"], item["tags"], item["source_url"], now),
            )
            if cur.rowcount:
                added += 1
            else:
                skipped += 1
        conn.commit()
    return added, skipped


def export_csv(db_path: Path, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, title, author, tags, source_url, parsed_at FROM items ORDER BY id"
        ).fetchall()
    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["id", "title", "author", "tags", "source_url", "parsed_at"])
        writer.writerows(rows)
    return len(rows)


def print_summary(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        top = conn.execute(
            "SELECT author, COUNT(*) c FROM items GROUP BY author ORDER BY c DESC LIMIT 5"
        ).fetchall()
    print(f"\nВсего записей в базе: {total}")
    if top:
        print("Топ авторов по количеству записей:")
        for author, count in top:
            print(f"  {author} — {count}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Парсер каталога в SQLite с отчётом в CSV")
    parser.add_argument("--pages", type=int, default=3, help="сколько страниц обойти (по умолчанию 3)")
    parser.add_argument("--out", type=Path, default=Path("data/report.csv"), help="путь к CSV-отчёту")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="путь к файлу базы SQLite")
    args = parser.parse_args()

    init_db(args.db)
    total_added = total_skipped = 0

    for page in range(1, args.pages + 1):
        try:
            html = fetch_page(page)
        except requests.RequestException as exc:
            print(f"Страница {page}: ошибка запроса — {exc}", file=sys.stderr)
            continue
        items = parse_page(html, page)
        added, skipped = save_items(args.db, items)
        total_added += added
        total_skipped += skipped
        print(f"Страница {page}: найдено {len(items)}, добавлено {added}, дублей {skipped}")

    print(f"\nИтого добавлено: {total_added}, пропущено дублей: {total_skipped}")
    count = export_csv(args.db, args.out)
    print(f"Отчёт сохранён: {args.out} ({count} строк)")
    print_summary(args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
