# -*- coding: utf-8 -*-
"""
db.py — заявки в SQLite. Без внешних зависимостей.
"""

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "orders.db")

STATUS_LABEL = {
    "new": "🆕 новая",
    "work": "🔧 в работе",
    "done": "✅ выполнен",
    "cancel": "❌ отменён",
}


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    conn = connect()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS orders (
               id       INTEGER PRIMARY KEY AUTOINCREMENT,
               created  TEXT,
               tg_id    TEXT,
               username TEXT,
               name     TEXT,
               phone    TEXT,
               item     TEXT,
               fabric   TEXT,
               qty      INTEGER,
               options  TEXT,
               total    INTEGER,
               status   TEXT DEFAULT 'new',
               comment  TEXT
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tg ON orders(tg_id)")
    conn.commit()
    conn.close()


def add_order(tg_id, username, name, phone, item, fabric, qty, options, total, comment=""):
    conn = connect()
    cur = conn.execute(
        """INSERT INTO orders(created,tg_id,username,name,phone,item,fabric,qty,options,total,comment)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            datetime.now().strftime("%d.%m.%Y %H:%M"),
            str(tg_id), username or "", name, phone,
            item, fabric, int(qty), options, int(total), comment or "",
        ),
    )
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id, "ШВ-%04d" % order_id


def get(order_id):
    conn = connect()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    return row


def by_status(status="new", limit=10):
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)
    ).fetchall()
    conn.close()
    return rows


def by_client(tg_id, limit=10):
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM orders WHERE tg_id=? ORDER BY id DESC LIMIT ?", (str(tg_id), limit)
    ).fetchall()
    conn.close()
    return rows


def set_status(order_id, status):
    conn = connect()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()


def stats():
    conn = connect()
    row = conn.execute(
        """SELECT COUNT(*) n,
                  COALESCE(SUM(total),0) sum_total,
                  SUM(CASE WHEN status='new' THEN 1 ELSE 0 END) n_new
           FROM orders"""
    ).fetchone()
    conn.close()
    return dict(row) if row else {"n": 0, "sum_total": 0, "n_new": 0}
