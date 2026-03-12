from __future__ import annotations

from pathlib import Path
import sqlite3


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA journal_mode=WAL;")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rootme_pseudo TEXT UNIQUE NOT NULL,
                rootme_id INTEGER,
                added_by TEXT,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
