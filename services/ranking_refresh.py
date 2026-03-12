from __future__ import annotations

import asyncio
import logging
import threading
import time

from config import Settings
from db.models import list_members, upsert_cached_score
from services.rootme_client import (
    RootMeApiError,
    RootMeAuthenticationError,
    RootMeClient,
    RootMeProfile,
    RootMeRateLimitError,
)


logger = logging.getLogger(__name__)


def start_ranking_refresh_loop(settings: Settings) -> None:
    thread = threading.Thread(
        target=_run_refresh_loop,
        args=(settings,),
        name="rootme-ranking-refresh",
        daemon=True,
    )
    thread.start()


def _run_refresh_loop(settings: Settings) -> None:
    while True:
        try:
            refresh_ranking_cache(settings)
        except Exception:
            logger.exception("Unexpected ranking refresh failure")
        time.sleep(max(settings.ranking_refresh_interval_seconds, 60))


def refresh_ranking_cache(settings: Settings) -> None:
    members = [member for member in list_members(settings.database_path) if member.rootme_id is not None]
    if not members:
        logger.info("Skipping ranking refresh because no tracked members are configured")
        return

    client = RootMeClient(
        api_key=settings.rootme_api_key,
        base_url=settings.rootme_api_base_url,
        request_delay_ms=settings.rootme_request_delay_ms,
        timeout_seconds=settings.rootme_timeout_seconds,
    )

    try:
        profiles = asyncio.run(
            client.get_profiles_by_ids(
                [member.rootme_id for member in members if member.rootme_id is not None]
            )
        )
    except (RootMeAuthenticationError, RootMeRateLimitError, RootMeApiError):
        logger.exception("Ranking cache refresh failed")
        return

    for profile in profiles:
        _store_profile_snapshot(settings, profile)

    logger.info("Ranking cache refreshed for %s tracked members", len(profiles))


def _store_profile_snapshot(settings: Settings, profile: RootMeProfile) -> None:
    upsert_cached_score(
        settings.database_path,
        rootme_id=profile.id,
        rootme_pseudo=profile.username,
        score=profile.score,
        global_rank=profile.global_rank,
        challenges_count=profile.challenges_count,
        profile_url=profile.profile_url,
        recent_resolutions=profile.recent_resolutions,
        fetched_at=profile.fetched_at,
    )
