from pathlib import Path
from datetime import UTC, datetime

from db.database import initialize_database
from db.models import (
    MemberAlreadyExistsError,
    MemberNotFoundError,
    add_member,
    delete_member,
    get_member_by_rootme_id,
    list_cached_scores_for_members,
    list_members,
    upsert_cached_score,
)
from services.rootme_client import ChallengeResolution


def test_add_and_delete_member_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.db"
    initialize_database(database_path)

    add_member(database_path, rootme_pseudo="alice", rootme_id=42, added_by="U123")

    member = get_member_by_rootme_id(database_path, 42)
    assert member is not None
    assert member.rootme_id == 42

    removed_member = delete_member(database_path, member.id)
    assert removed_member.rootme_pseudo == "alice"
    assert list_members(database_path) == []


def test_add_member_allows_distinct_case_variant(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.db"
    initialize_database(database_path)

    add_member(database_path, rootme_pseudo="Alice", rootme_id=42, added_by="U123")
    add_member(database_path, rootme_pseudo="alice", rootme_id=43, added_by="U999")

    members = list_members(database_path)
    assert len(members) == 2


def test_add_member_rejects_exact_duplicate(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.db"
    initialize_database(database_path)

    add_member(database_path, rootme_pseudo="Alice", rootme_id=42, added_by="U123")

    try:
        add_member(database_path, rootme_pseudo="Alice", rootme_id=42, added_by="U999")
    except MemberAlreadyExistsError:
        pass
    else:
        raise AssertionError("Expected MemberAlreadyExistsError")


def test_delete_member_raises_for_unknown_member(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.db"
    initialize_database(database_path)

    try:
        delete_member(database_path, 999)
    except MemberNotFoundError:
        pass
    else:
        raise AssertionError("Expected MemberNotFoundError")


def test_list_cached_scores_for_members_returns_only_tracked_members(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.db"
    initialize_database(database_path)

    add_member(database_path, rootme_pseudo="alice", rootme_id=42, added_by="U123")
    upsert_cached_score(
        database_path,
        rootme_id=42,
        rootme_pseudo="alice",
        score=100,
        global_rank=10,
        challenges_count=5,
        profile_url="https://www.root-me.org/alice",
        recent_resolutions=(
            ChallengeResolution(title="XSS 101", validated_at="2026-03-10"),
        ),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )
    upsert_cached_score(
        database_path,
        rootme_id=99,
        rootme_pseudo="ghost",
        score=1,
        global_rank=999,
        challenges_count=1,
        profile_url="https://www.root-me.org/ghost",
        recent_resolutions=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    cached_scores = list_cached_scores_for_members(database_path)

    assert len(cached_scores) == 1
    assert cached_scores[0].rootme_id == 42
    assert cached_scores[0].recent_resolutions[0].title == "XSS 101"
