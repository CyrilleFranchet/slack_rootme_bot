from __future__ import annotations

import asyncio
import logging
import threading
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import Settings
from db.models import get_cached_score_by_rootme_id, list_members, upsert_cached_score
from services.rootme_client import (
    ChallengeResolution,
    RootMeApiError,
    RootMeAuthenticationError,
    RootMeClient,
    RootMeProfile,
    RootMeRateLimitError,
)
from utils.formatter import build_challenge_solved_blocks


logger = logging.getLogger(__name__)


def start_ranking_refresh_loop(settings: Settings, *, run_immediately: bool = True) -> None:
    thread = threading.Thread(
        target=_run_refresh_loop,
        args=(settings, run_immediately),
        name="rootme-ranking-refresh",
        daemon=True,
    )
    thread.start()


def _run_refresh_loop(settings: Settings, run_immediately: bool) -> None:
    if not run_immediately:
        time.sleep(max(settings.ranking_refresh_interval_seconds, 60))
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

    slack_client = _build_slack_client(settings)
    for profile in profiles:
        previous_snapshot = get_cached_score_by_rootme_id(settings.database_path, profile.id)
        cache_profile_snapshot(settings, profile)
        _announce_new_resolutions(
            settings,
            slack_client=slack_client,
            profile=profile,
            previous_snapshot=previous_snapshot,
        )

    logger.info("Ranking cache refreshed for %s tracked members", len(profiles))


def cache_profile_snapshot(settings: Settings, profile: RootMeProfile) -> None:
    upsert_cached_score(
        settings.database_path,
        rootme_id=profile.id,
        rootme_pseudo=profile.username,
        score=profile.score,
        rootme_rank=profile.rootme_rank,
        rootme_position=profile.rootme_position,
        challenges_count=profile.challenges_count,
        profile_url=profile.profile_url,
        recent_resolutions=profile.recent_resolutions,
        fetched_at=profile.fetched_at,
    )


def _build_slack_client(settings: Settings) -> WebClient | None:
    if not settings.slack_activity_channel_id:
        return None
    return WebClient(token=settings.slack_bot_token)


def _announce_new_resolutions(
    settings: Settings,
    *,
    slack_client: WebClient | None,
    profile: RootMeProfile,
    previous_snapshot,
) -> None:
    if slack_client is None or previous_snapshot is None:
        return

    known_resolutions = {
        (resolution.title, resolution.validated_at)
        for resolution in previous_snapshot.recent_resolutions
    }
    new_resolutions = [
        resolution
        for resolution in profile.recent_resolutions
        if (resolution.title, resolution.validated_at) not in known_resolutions
    ]
    if not new_resolutions:
        return

    try:
        slack_client.chat_postMessage(
            channel=settings.slack_activity_channel_id,
            blocks=build_challenge_solved_blocks(profile, new_resolutions),
            text=f"{profile.username} solved new Root-Me challenges.",
        )
    except SlackApiError:
        logger.exception(
            "Failed to post Root-Me activity notification",
            extra={"rootme_id": profile.id, "username": profile.username},
        )
