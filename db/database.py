from __future__ import annotations

from pathlib import Path
import sqlite3


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA journal_mode=WAL;")
        _migrate_members_table(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_scores (
                rootme_id INTEGER PRIMARY KEY,
                rootme_pseudo TEXT NOT NULL,
                score INTEGER NOT NULL,
                rootme_rank INTEGER,
                rootme_position INTEGER,
                challenges_count INTEGER NOT NULL,
                profile_url TEXT NOT NULL,
                recent_resolutions_json TEXT NOT NULL DEFAULT '[]',
                fetched_at TEXT NOT NULL
            )
            """
        )
        _migrate_cache_scores_table(connection)


def _migrate_members_table(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table' AND name = 'members'
        """
    ).fetchone()

    desired_sql = """
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rootme_pseudo TEXT NOT NULL,
            rootme_id INTEGER UNIQUE,
            added_by TEXT,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """

    if row is None:
        connection.execute(desired_sql)
        return

    current_sql = (row[0] or "").lower()
    if "rootme_pseudo text unique" not in current_sql and "rootme_id integer unique" in current_sql:
        return

    connection.execute("ALTER TABLE members RENAME TO members_legacy")
    connection.execute(desired_sql)
    connection.execute(
        """
        INSERT OR IGNORE INTO members (id, rootme_pseudo, rootme_id, added_by, added_at)
        SELECT id, rootme_pseudo, rootme_id, added_by, added_at
        FROM members_legacy
        """
    )
    connection.execute("DROP TABLE members_legacy")


def _migrate_cache_scores_table(connection: sqlite3.Connection) -> None:
    existing_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(cache_scores)").fetchall()
    }
    if "rootme_rank" not in existing_columns and "global_rank" in existing_columns:
        connection.execute(
            """
            ALTER TABLE cache_scores
            RENAME COLUMN global_rank TO rootme_rank
            """
        )
        existing_columns.remove("global_rank")
        existing_columns.add("rootme_rank")
    if "rootme_position" not in existing_columns:
        connection.execute(
            """
            ALTER TABLE cache_scores
            ADD COLUMN rootme_position INTEGER
            """
        )
        existing_columns.add("rootme_position")
    if "recent_resolutions_json" not in existing_columns:
        connection.execute(
            """
            ALTER TABLE cache_scores
            ADD COLUMN recent_resolutions_json TEXT NOT NULL DEFAULT '[]'
            """
        )
