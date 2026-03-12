from datetime import UTC, datetime

from services.ranking import RankingEntry
from services.rootme_client import RootMeProfile
from utils.formatter import (
    build_help_blocks,
    build_member_added_blocks,
    build_profile_blocks,
    build_ranking_blocks,
    build_remove_confirmation_blocks,
)


def test_build_help_blocks_contains_help_command() -> None:
    blocks = build_help_blocks()

    section_texts = [
        block["text"]["text"]
        for block in blocks
        if block["type"] == "section"
    ]

    assert any("/rootme help" in text for text in section_texts)


def test_build_ranking_blocks_contains_profile_data() -> None:
    profile = RootMeProfile(
        id=42,
        username="alice",
        score=2450,
        global_rank=1203,
        challenges_count=385,
        profile_url="https://www.root-me.org/alice",
        categories=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_ranking_blocks(
        [RankingEntry(position=1, profile=profile)],
        updated_at=profile.fetched_at,
    )

    assert "alice" in blocks[1]["text"]["text"]
    assert "#1,203 worldwide" in blocks[1]["text"]["text"]


def test_build_profile_blocks_contains_category_section() -> None:
    profile = RootMeProfile(
        id=7,
        username="bob",
        score=500,
        global_rank=999,
        challenges_count=10,
        profile_url="https://www.root-me.org/bob",
        categories=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_profile_blocks(profile)

    assert "bob" in blocks[0]["text"]["text"]
    assert "https://www.root-me.org/bob" in blocks[1]["text"]["text"]


def test_build_member_added_blocks_contains_username() -> None:
    profile = RootMeProfile(
        id=8,
        username="carol",
        score=800,
        global_rank=111,
        challenges_count=20,
        profile_url="https://www.root-me.org/carol",
        categories=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_member_added_blocks(profile)

    assert "carol" in blocks[1]["text"]["text"]


def test_build_remove_confirmation_blocks_contains_buttons() -> None:
    blocks = build_remove_confirmation_blocks("dave")

    assert blocks[2]["type"] == "actions"
    assert len(blocks[2]["elements"]) == 2
