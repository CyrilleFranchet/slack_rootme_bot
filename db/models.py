from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from services.rootme_client import ChallengeResolution


@dataclass(frozen=True)
class Member:
    id: int
    rootme_pseudo: str
    rootme_id: int | None
    added_by: str | None
    added_at: str


@dataclass(frozen=True)
class CachedScore:
    rootme_id: int
    rootme_pseudo: str
    score: int
    rootme_rank: int | None
    rootme_position: int | None
    challenges_count: int
    profile_url: str
    recent_resolutions: tuple[ChallengeResolution, ...]
    fetched_at: datetime


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
        if member.rootme_id is not None:
            connection.execute(
                """
                DELETE FROM cache_scores
                WHERE rootme_id = ?
                """,
                (member.rootme_id,),
            )

    return member


def upsert_cached_score(
    database_path: Path,
    *,
    rootme_id: int,
    rootme_pseudo: str,
    score: int,
    rootme_rank: int | None,
    rootme_position: int | None,
    challenges_count: int,
    profile_url: str,
    recent_resolutions: tuple[ChallengeResolution, ...],
    fetched_at: datetime,
) -> None:
    recent_resolutions_json = json.dumps(
        [
            {
                "title": resolution.title,
                "validated_at": resolution.validated_at,
            }
            for resolution in recent_resolutions
        ]
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO cache_scores (
                rootme_id,
                rootme_pseudo,
                score,
                rootme_rank,
                rootme_position,
                challenges_count,
                profile_url,
                recent_resolutions_json,
                fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rootme_id) DO UPDATE SET
                rootme_pseudo = excluded.rootme_pseudo,
                score = excluded.score,
                rootme_rank = excluded.rootme_rank,
                rootme_position = excluded.rootme_position,
                challenges_count = excluded.challenges_count,
                profile_url = excluded.profile_url,
                recent_resolutions_json = excluded.recent_resolutions_json,
                fetched_at = excluded.fetched_at
            """,
            (
                rootme_id,
                rootme_pseudo,
                score,
                rootme_rank,
                rootme_position,
                challenges_count,
                profile_url,
                recent_resolutions_json,
                fetched_at.isoformat(),
            ),
        )


def get_cached_score_by_rootme_id(database_path: Path, rootme_id: int) -> CachedScore | None:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT
                rootme_id,
                rootme_pseudo,
                score,
                rootme_rank,
                rootme_position,
                challenges_count,
                profile_url,
                recent_resolutions_json,
                fetched_at
            FROM cache_scores
            WHERE rootme_id = ?
            """,
            (rootme_id,),
        ).fetchone()

    if row is None:
        return None
    return _row_to_cached_score(row)


def list_cached_scores_for_members(database_path: Path) -> list[CachedScore]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                cache_scores.rootme_id,
                cache_scores.rootme_pseudo,
                cache_scores.score,
                cache_scores.rootme_rank,
                cache_scores.rootme_position,
                cache_scores.challenges_count,
                cache_scores.profile_url,
                cache_scores.recent_resolutions_json,
                cache_scores.fetched_at
            FROM cache_scores
            INNER JOIN members ON members.rootme_id = cache_scores.rootme_id
            ORDER BY cache_scores.score DESC, cache_scores.rootme_pseudo ASC
            """
        ).fetchall()

    return [_row_to_cached_score(row) for row in rows]


def _row_to_member(row: tuple[object, ...]) -> Member:
    return Member(
        id=int(row[0]),
        rootme_pseudo=str(row[1]),
        rootme_id=int(row[2]) if row[2] is not None else None,
        added_by=str(row[3]) if row[3] is not None else None,
        added_at=str(row[4]),
    )


def _row_to_cached_score(row: tuple[object, ...]) -> CachedScore:
    resolutions_payload = json.loads(str(row[6]))
    recent_resolutions = tuple(
        ChallengeResolution(
            title=str(item.get("title", "")),
            validated_at=(
                str(item["validated_at"])
                if item.get("validated_at") is not None
                else None
            ),
        )
        for item in resolutions_payload
        if isinstance(item, dict) and item.get("title")
    )
    return CachedScore(
        rootme_id=int(row[0]),
        rootme_pseudo=str(row[1]),
        score=int(row[2]),
        rootme_rank=int(row[3]) if row[3] is not None else None,
        rootme_position=int(row[4]) if row[4] is not None else None,
        challenges_count=int(row[5]),
        profile_url=str(row[6]),
        recent_resolutions=recent_resolutions,
        fetched_at=datetime.fromisoformat(str(row[8])),
    )
