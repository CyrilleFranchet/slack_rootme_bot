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
            ORDER BY rootme_pseudo ASC, rootme_id ASC, id ASC
            """
        ).fetchall()

    return [_row_to_member(row) for row in rows]


def list_members_by_pseudo(database_path: Path, rootme_pseudo: str) -> list[Member]:
    normalized_pseudo = rootme_pseudo.strip()
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, rootme_pseudo, rootme_id, added_by, added_at
            FROM members
            WHERE rootme_pseudo = ?
            ORDER BY rootme_id ASC, id ASC
            """,
            (normalized_pseudo,),
        ).fetchall()

    return [_row_to_member(row) for row in rows]


def get_member_by_id(database_path: Path, member_id: int) -> Member | None:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, rootme_pseudo, rootme_id, added_by, added_at
            FROM members
            WHERE id = ?
            """,
            (member_id,),
        ).fetchone()

    if row is None:
        return None
    return _row_to_member(row)


def get_member_by_rootme_id(database_path: Path, rootme_id: int) -> Member | None:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, rootme_pseudo, rootme_id, added_by, added_at
            FROM members
            WHERE rootme_id = ?
            """,
            (rootme_id,),
        ).fetchone()

    if row is None:
        return None
    return _row_to_member(row)


def add_member(
    database_path: Path,
    *,
    rootme_pseudo: str,
    rootme_id: int | None = None,
    added_by: str | None = None,
) -> None:
    normalized_pseudo = rootme_pseudo.strip()
    with sqlite3.connect(database_path) as connection:
        if rootme_id is not None:
            existing_row = connection.execute(
                """
                SELECT id
                FROM members
                WHERE rootme_id = ?
                """,
                (rootme_id,),
            ).fetchone()
            if existing_row is not None:
                raise MemberAlreadyExistsError(
                    f"The Root-Me account with ID `{rootme_id}` is already tracked."
                )

        connection.execute(
            """
            INSERT INTO members (rootme_pseudo, rootme_id, added_by)
            VALUES (?, ?, ?)
            """,
            (normalized_pseudo, rootme_id, added_by),
        )


def delete_member(database_path: Path, member_id: int) -> Member:
    member = get_member_by_id(database_path, member_id)
    if member is None:
        raise MemberNotFoundError(f"The tracked member with ID `{member_id}` was not found.")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            DELETE FROM members
            WHERE id = ?
            """,
            (member.id,),
        )

    return member


def _row_to_member(row: tuple[object, ...]) -> Member:
    return Member(
        id=int(row[0]),
        rootme_pseudo=str(row[1]),
        rootme_id=int(row[2]) if row[2] is not None else None,
        added_by=str(row[3]) if row[3] is not None else None,
        added_at=str(row[4]),
    )
