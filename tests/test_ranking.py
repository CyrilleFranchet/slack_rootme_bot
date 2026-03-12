from datetime import UTC, datetime

from services.ranking import build_ranking
from services.rootme_client import RootMeProfile


def test_build_ranking_sorts_by_score_descending() -> None:
    fetched_at = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)
    low = RootMeProfile(
        id=1,
        username="low",
        score=10,
        global_rank=100,
        challenges_count=1,
        profile_url="https://www.root-me.org/low",
        categories=(),
        recent_resolutions=(),
        fetched_at=fetched_at,
    )
    high = RootMeProfile(
        id=2,
        username="high",
        score=50,
        global_rank=10,
        challenges_count=5,
        profile_url="https://www.root-me.org/high",
        categories=(),
        recent_resolutions=(),
        fetched_at=fetched_at,
    )

    ranking = build_ranking([low, high])

    assert ranking[0].profile.username == "high"
    assert ranking[1].profile.username == "low"
