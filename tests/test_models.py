from pathlib import Path

from db.database import initialize_database
from db.models import (
    MemberAlreadyExistsError,
    MemberNotFoundError,
    add_member,
    delete_member,
    get_member_by_pseudo,
    list_members,
)


def test_add_and_delete_member_round_trip(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.db"
    initialize_database(database_path)

    add_member(database_path, rootme_pseudo="alice", rootme_id=42, added_by="U123")

    member = get_member_by_pseudo(database_path, "alice")
    assert member is not None
    assert member.rootme_id == 42

    removed_member = delete_member(database_path, "alice")
    assert removed_member.rootme_pseudo == "alice"
    assert list_members(database_path) == []


def test_add_member_rejects_duplicate_case_insensitive(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.db"
    initialize_database(database_path)

    add_member(database_path, rootme_pseudo="Alice", rootme_id=42, added_by="U123")

    try:
        add_member(database_path, rootme_pseudo="alice", rootme_id=42, added_by="U999")
    except MemberAlreadyExistsError:
        pass
    else:
        raise AssertionError("Expected MemberAlreadyExistsError")


def test_delete_member_raises_for_unknown_member(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.db"
    initialize_database(database_path)

    try:
        delete_member(database_path, "ghost")
    except MemberNotFoundError:
        pass
    else:
        raise AssertionError("Expected MemberNotFoundError")
