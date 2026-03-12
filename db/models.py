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


class MemberAlreadyExistsError(Exception):
    """Raised when a tracked member already exists in the local database."""


class MemberNotFoundError(Exception):
    """Raised when a tracked member cannot be found in the local database."""


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
    normalized_pseudo = rootme_pseudo.strip()
    with sqlite3.connect(database_path) as connection:
        existing_row = connection.execute(
            """
            SELECT id
            FROM members
            WHERE lower(rootme_pseudo) = lower(?)
            """,
            (normalized_pseudo,),
        ).fetchone()

        if existing_row is not None:
            raise MemberAlreadyExistsError(
                f"The Root-Me username `{normalized_pseudo}` is already tracked."
            )

        connection.execute(
            """
            INSERT INTO members (rootme_pseudo, rootme_id, added_by)
            VALUES (?, ?, ?)
            """,
            (normalized_pseudo, rootme_id, added_by),
        )


def get_member_by_pseudo(database_path: Path, rootme_pseudo: str) -> Member | None:
    normalized_pseudo = rootme_pseudo.strip()
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, rootme_pseudo, rootme_id, added_by, added_at
            FROM members
            WHERE lower(rootme_pseudo) = lower(?)
            """,
            (normalized_pseudo,),
        ).fetchone()

    if row is None:
        return None

    return Member(
        id=row[0],
        rootme_pseudo=row[1],
        rootme_id=row[2],
        added_by=row[3],
        added_at=row[4],
    )


def delete_member(database_path: Path, rootme_pseudo: str) -> Member:
    member = get_member_by_pseudo(database_path, rootme_pseudo)
    if member is None:
        raise MemberNotFoundError(
            f"The Root-Me username `{rootme_pseudo.strip()}` is not tracked."
        )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            DELETE FROM members
            WHERE id = ?
            """,
            (member.id,),
        )

    return member
