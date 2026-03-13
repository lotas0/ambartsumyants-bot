import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    tg_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    photo_file_id TEXT,
    price TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    photo_file_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    weight TEXT,
    size TEXT,
    comment TEXT,
    contact TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""


class Database:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.executescript(DB_SCHEMA)

    # users
    def get_or_create_user(self, tg_id: int, username: str | None, full_name: str | None) -> int:
        with self._connection() as conn:
            cur = conn.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
            row = cur.fetchone()
            if row:
                return int(row["id"])
            cur = conn.execute(
                "INSERT INTO users (tg_id, username, full_name) VALUES (?, ?, ?)",
                (tg_id, username, full_name),
            )
            return int(cur.lastrowid)

    # products
    def add_product(self, title: str, description: str, price: str | None, photo_file_id: str | None) -> int:
        with self._connection() as conn:
            cur = conn.execute(
                "INSERT INTO products (title, description, price, photo_file_id) VALUES (?, ?, ?, ?)",
                (title, description, price, photo_file_id),
            )
            return int(cur.lastrowid)

    def list_active_products(self) -> list[sqlite3.Row]:
        with self._connection() as conn:
            cur = conn.execute(
                "SELECT * FROM products WHERE is_active = 1 ORDER BY created_at DESC"
            )
            return list(cur.fetchall())

    def list_all_products(self) -> list[sqlite3.Row]:
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM products ORDER BY created_at DESC")
            return list(cur.fetchall())

    def set_product_active(self, product_id: int, is_active: bool) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE products SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, product_id),
            )

    def delete_product(self, product_id: int) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

    # portfolio
    def add_portfolio_item(self, title: str | None, photo_file_id: str) -> int:
        with self._connection() as conn:
            cur = conn.execute(
                "INSERT INTO portfolio (title, photo_file_id) VALUES (?, ?)",
                (title, photo_file_id),
            )
            return int(cur.lastrowid)

    def list_portfolio(self) -> list[sqlite3.Row]:
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM portfolio ORDER BY created_at DESC")
            return list(cur.fetchall())

    def delete_portfolio_item(self, item_id: int) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM portfolio WHERE id = ?", (item_id,))

    # orders
    def add_order(
        self,
        user_id: int | None,
        weight: str,
        size: str,
        comment: str | None,
        contact: str,
    ) -> int:
        with self._connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO orders (user_id, weight, size, comment, contact)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, weight, size, comment, contact),
            )
            return int(cur.lastrowid)

    def list_orders(self, status: str | None = None) -> list[sqlite3.Row]:
        with self._connection() as conn:
            if status:
                cur = conn.execute(
                    "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                )
            else:
                cur = conn.execute("SELECT * FROM orders ORDER BY created_at DESC")
            return list(cur.fetchall())

    def update_order_status(self, order_id: int, status: str) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status, order_id),
            )

    def get_order(self, order_id: int) -> sqlite3.Row | None:
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            return cur.fetchone()

    # broadcast helpers
    def get_all_user_tg_ids(self) -> list[int]:
        with self._connection() as conn:
            cur = conn.execute("SELECT tg_id FROM users")
            return [int(r["tg_id"]) for r in cur.fetchall()]

    def execute_many(self, sql: str, params_seq: Iterable[Iterable[Any]]) -> None:
        with self._connection() as conn:
            conn.executemany(sql, params_seq)

