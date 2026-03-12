from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class Member:
    id: int
    rootme_pseudo: str
    rootme_id: int | None
    added_by: str | None
    added_at: str


def list_members(database_path: Path) -> list[Member]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, rootme_pseudo, rootme_id, added_by, added_at
            FROM members
            ORDER BY lower(rootme_pseudo) ASC
            """
        ).fetchall()

    return [
        Member(
            id=row[0],
            rootme_pseudo=row[1],
            rootme_id=row[2],
            added_by=row[3],
            added_at=row[4],
        )
        for row in rows
    ]


def add_member(
    database_path: Path,
    *,
    rootme_pseudo: str,
    rootme_id: int | None = None,
    added_by: str | None = None,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO members (rootme_pseudo, rootme_id, added_by)
            VALUES (?, ?, ?)
            ON CONFLICT(rootme_pseudo) DO UPDATE SET
                rootme_id = excluded.rootme_id,
                added_by = COALESCE(excluded.added_by, members.added_by)
            """,
            (rootme_pseudo, rootme_id, added_by),
        )
