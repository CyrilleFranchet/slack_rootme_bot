from datetime import UTC, datetime

from services.ranking import RankingEntry
from services.rootme_client import ChallengeResolution, RootMeProfile
from utils.formatter import (
    build_add_confirmation_blocks,
    build_candidate_selection_blocks,
    build_challenge_solved_blocks,
    build_detailed_ranking_blocks,
    build_help_blocks,
    build_member_added_blocks,
    build_member_list_blocks,
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
        rootme_rank="1203",
        rootme_position=4521,
        challenges_count=385,
        profile_url="https://www.root-me.org/alice",
        categories=(),
        recent_resolutions=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_ranking_blocks(
        [RankingEntry(position=1, profile=profile)],
        updated_at=profile.fetched_at,
    )

    assert "alice" in blocks[1]["text"]["text"]
    assert "rank #1,203" in blocks[1]["text"]["text"]
    assert "position #4,521" in blocks[1]["text"]["text"]


def test_build_detailed_ranking_blocks_contains_recent_challenges() -> None:
    profile = RootMeProfile(
        id=42,
        username="alice",
        score=2450,
        rootme_rank="1203",
        rootme_position=4521,
        challenges_count=385,
        profile_url="https://www.root-me.org/alice",
        categories=(),
        recent_resolutions=(
            ChallengeResolution(title="JWT - Revoked token", validated_at="2026-03-11 21:05:03"),
        ),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_detailed_ranking_blocks(
        [RankingEntry(position=1, profile=profile)],
        updated_at=profile.fetched_at,
    )

    assert "alice" in blocks[1]["text"]["text"]
    assert "JWT - Revoked token" in blocks[2]["text"]["text"]


def test_build_challenge_solved_blocks_contains_username_and_challenges() -> None:
    profile = RootMeProfile(
        id=42,
        username="alice",
        score=2450,
        rootme_rank="1203",
        rootme_position=4521,
        challenges_count=385,
        profile_url="https://www.root-me.org/alice",
        categories=(),
        recent_resolutions=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_challenge_solved_blocks(
        profile,
        [
            ChallengeResolution(
                title="JWT - Revoked token",
                validated_at="2026-03-11 21:05:03",
            )
        ],
    )

    assert "alice" in blocks[1]["text"]["text"]
    assert "JWT - Revoked token" in blocks[2]["text"]["text"]


def test_build_challenge_solved_blocks_can_include_extra_message() -> None:
    profile = RootMeProfile(
        id=42,
        username="alice",
        score=2450,
        rootme_rank="1203",
        rootme_position=4521,
        challenges_count=385,
        profile_url="https://www.root-me.org/alice",
        categories=(),
        recent_resolutions=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_challenge_solved_blocks(
        profile,
        [
            ChallengeResolution(
                title="JWT - Revoked token",
                validated_at="2026-03-11 21:05:03",
            )
        ],
        extra_message="That flag probably regrets existing.",
    )

    assert blocks[3]["type"] == "context"
    assert "regrets existing" in blocks[3]["elements"][0]["text"]


def test_build_profile_blocks_contains_category_section() -> None:
    profile = RootMeProfile(
        id=7,
        username="bob",
        score=500,
        rootme_rank="insider",
        rootme_position=1500,
        challenges_count=10,
        profile_url="https://www.root-me.org/bob",
        categories=(),
        recent_resolutions=(
            ChallengeResolution(
                title="SQL injection - Authentication",
                validated_at="2026-03-10",
            ),
        ),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_profile_blocks(profile)

    assert "bob" in blocks[0]["text"]["text"]
    assert "Root-Me ID" in blocks[1]["text"]["text"]
    assert "Root-Me rank" in blocks[1]["text"]["text"]
    assert "Root-Me position" in blocks[1]["text"]["text"]
    assert "2026-03-10" in blocks[2]["text"]["text"]


def test_build_member_added_blocks_contains_username() -> None:
    profile = RootMeProfile(
        id=8,
        username="carol",
        score=800,
        rootme_rank="111",
        rootme_position=222,
        challenges_count=20,
        profile_url="https://www.root-me.org/carol",
        categories=(),
        recent_resolutions=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_member_added_blocks(profile)

    assert "carol" in blocks[1]["text"]["text"]


def test_build_add_confirmation_blocks_contains_actions() -> None:
    profile = RootMeProfile(
        id=8,
        username="carol",
        score=800,
        rootme_rank="111",
        rootme_position=222,
        challenges_count=20,
        profile_url="https://www.root-me.org/carol",
        categories=(),
        recent_resolutions=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_add_confirmation_blocks(profile)

    assert blocks[-1]["type"] == "actions"
    assert len(blocks[-1]["elements"]) == 2


def test_build_member_list_blocks_contains_adder() -> None:
    blocks = build_member_list_blocks(
        [
            {
                "rootme_pseudo": "alice",
                "rootme_id": "42",
                "added_by": "<@U123>",
            }
        ]
    )

    assert "alice" in blocks[1]["text"]["text"]
    assert "<@U123>" in blocks[1]["text"]["text"]


def test_build_remove_confirmation_blocks_contains_buttons() -> None:
    blocks = build_remove_confirmation_blocks(12, "dave", 34)

    assert blocks[2]["type"] == "actions"
    assert len(blocks[2]["elements"]) == 2


def test_build_candidate_selection_blocks_contains_rootme_id() -> None:
    profile = RootMeProfile(
        id=42,
        username="alice",
        score=2450,
        rootme_rank="1203",
        rootme_position=4521,
        challenges_count=385,
        profile_url="https://www.root-me.org/alice",
        categories=(),
        recent_resolutions=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )

    blocks = build_candidate_selection_blocks(
        title="Select profile",
        body="Choose one.",
        profiles=[profile],
        action_id="select_profile_candidate",
    )

    assert "ID `42`" in blocks[2]["text"]["text"]
