from __future__ import annotations

from dataclasses import dataclass

from services.rootme_client import RootMeProfile


@dataclass(frozen=True)
class RankingEntry:
    position: int
    profile: RootMeProfile


def build_ranking(profiles: list[RootMeProfile]) -> list[RankingEntry]:
    sorted_profiles = sorted(
        profiles,
        key=lambda profile: (-profile.score, profile.username.lower()),
    )
    return [
        RankingEntry(position=index, profile=profile)
        for index, profile in enumerate(sorted_profiles, start=1)
    ]
