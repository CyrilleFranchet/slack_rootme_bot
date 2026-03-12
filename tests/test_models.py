from pathlib import Path

from db.database import initialize_database
from db.models import (
    MemberAlreadyExistsError,
    MemberNotFoundError,
    add_member,
    delete_member,
    get_member_by_rootme_id,
    list_members,
)


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
