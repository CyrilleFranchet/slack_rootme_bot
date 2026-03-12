from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from slack_bolt import App

from config import Settings
from db.models import (
    MemberAlreadyExistsError,
    add_member,
    get_member_by_rootme_id,
    list_cached_scores_for_members,
    list_members,
    list_members_by_pseudo,
)
from services.ranking import build_ranking
from services.rootme_client import (
    RootMeApiError,
    RootMeAuthenticationError,
    RootMeClient,
    RootMeProfile,
    RootMeRateLimitError,
)
from utils.formatter import (
    build_add_confirmation_blocks,
    build_candidate_selection_blocks,
    build_empty_ranking_blocks,
    build_error_blocks,
    build_help_blocks,
    build_member_added_blocks,
    build_profile_blocks,
    build_remove_confirmation_blocks,
    build_ranking_blocks,
)


SUPPORTED_SUBCOMMANDS = {
    "help",
    "aide",
    "ranking",
    "classement",
    "profile",
    "profil",
    "add",
    "ajouter",
    "remove",
    "supprimer",
}


def register_commands(app: App, settings: Settings) -> None:
    @app.command("/rootme")
    def handle_rootme_command(ack: Any, respond: Any, command: dict[str, Any]) -> None:
        text = (command.get("text") or "").strip()
        parts = text.split()
        subcommand = parts[0].lower() if parts else "help"

        if subcommand in {"help", "aide"}:
            ack()
            respond(blocks=build_help_blocks(), response_type="ephemeral")
            return

        if subcommand in {"ranking", "classement"}:
            ack(text="Fetching the Root-Me ranking...")
            _handle_ranking_command(
                respond,
                settings=settings,
            )
            return

        if subcommand in {"profile", "profil"}:
            ack(text="Fetching the Root-Me profile...")
            _handle_profile_command(
                respond,
                rootme_client=_build_rootme_client(settings),
                username=" ".join(parts[1:]).strip(),
            )
            return

        if subcommand in {"add", "ajouter"}:
            ack(text="Validating the Root-Me profile...")
            _handle_add_command(
                respond,
                settings=settings,
                rootme_client=_build_rootme_client(settings),
                username=" ".join(parts[1:]).strip(),
            )
            return

        if subcommand in {"remove", "supprimer"}:
            ack()
            _handle_remove_command(
                respond,
                settings=settings,
                username=" ".join(parts[1:]).strip(),
                rootme_client=_build_rootme_client(settings),
            )
            return

        ack()
        respond(
            text=(
                f"Unknown subcommand `{subcommand}`. "
                "Use `/rootme help` to see the available commands."
            ),
            blocks=build_help_blocks(
                title="Unknown subcommand",
                body=(
                    f"`{subcommand}` is not supported. "
                    "Use `/rootme help` to view the current command set."
                ),
            ),
            response_type="ephemeral",
        )


def _handle_ranking_command(
    respond: Any,
    *,
    settings: Settings,
) -> None:
    members = list_members(settings.database_path)
    if not members:
        respond(blocks=build_empty_ranking_blocks(), response_type="ephemeral")
        return

    cached_scores = list_cached_scores_for_members(settings.database_path)
    if not cached_scores:
        respond(
            blocks=build_error_blocks(
                title="Ranking cache is empty",
                body="No cached ranking data is available yet. Wait for the background refresh to run, then try again.",
            ),
            response_type="ephemeral",
        )
        return

    profiles = [
        RootMeProfile(
            id=cached.rootme_id,
            username=cached.rootme_pseudo,
            score=cached.score,
            global_rank=cached.global_rank,
            challenges_count=cached.challenges_count,
            profile_url=cached.profile_url,
            categories=(),
            fetched_at=cached.fetched_at,
        )
        for cached in cached_scores
    ]

    ranking_entries = build_ranking(profiles)
    updated_at = max(
        (entry.profile.fetched_at for entry in ranking_entries),
        default=datetime.now(UTC),
    )
    respond(
        blocks=build_ranking_blocks(ranking_entries, updated_at=updated_at),
        response_type="in_channel",
    )


def _handle_profile_command(
    respond: Any,
    *,
    rootme_client: RootMeClient,
    username: str,
) -> None:
    if not username:
        respond(
            blocks=build_error_blocks(
                title="Missing username",
                body="Usage: `/rootme profile <username>`",
            ),
            response_type="ephemeral",
        )
        return

    profiles = _search_profiles_or_respond(respond, rootme_client=rootme_client, username=username)
    if profiles is None:
        return

    if len(profiles) > 1:
        respond(
            blocks=build_candidate_selection_blocks(
                title=":mag: Multiple Root-Me profiles found",
                body="More than one Root-Me account matches that username. Choose the correct account.",
                profiles=profiles,
                action_id="select_profile_candidate",
            ),
            response_type="ephemeral",
        )
        return

    respond(blocks=build_profile_blocks(profiles[0]), response_type="ephemeral")


def _handle_add_command(
    respond: Any,
    *,
    settings: Settings,
    rootme_client: RootMeClient,
    username: str,
) -> None:
    if not username:
        respond(
            blocks=build_error_blocks(
                title="Missing Root-Me ID",
                body="Usage: `/rootme add <rootme_id>`",
            ),
            response_type="ephemeral",
        )
        return

    try:
        rootme_id = int(username)
    except ValueError:
        respond(
            blocks=build_error_blocks(
                title="Invalid Root-Me ID",
                body="Usage: `/rootme add <rootme_id>` with a numeric Root-Me account ID.",
            ),
            response_type="ephemeral",
        )
        return

    if get_member_by_rootme_id(settings.database_path, rootme_id) is not None:
        respond(
            blocks=build_error_blocks(
                title="Member already tracked",
                body=f"The Root-Me account with ID `{rootme_id}` is already in the tracked member list.",
            ),
            response_type="ephemeral",
        )
        return

    try:
        profile = asyncio.run(rootme_client.get_profile_by_id(rootme_id))
    except RootMeAuthenticationError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me authentication failed",
                body="The configured `ROOTME_API_KEY` was rejected by Root-Me. Update the API key and restart the bot.",
            ),
            response_type="ephemeral",
        )
        return
    except RootMeRateLimitError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me rate limit reached",
                body="Root-Me is temporarily rate limiting requests. Wait a bit and try the command again.",
            ),
            response_type="ephemeral",
        )
        return
    except RootMeApiError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me API unavailable",
                body="The Root-Me API is temporarily unavailable. Please try again in a few minutes.",
            ),
            response_type="ephemeral",
        )
        return

    respond(blocks=build_add_confirmation_blocks(profile), response_type="ephemeral")


def _handle_remove_command(
    respond: Any,
    *,
    settings: Settings,
    username: str,
    rootme_client: RootMeClient,
) -> None:
    if not username:
        respond(
            blocks=build_error_blocks(
                title="Missing username",
                body="Usage: `/rootme remove <username>`",
            ),
            response_type="ephemeral",
        )
        return

    members = list_members_by_pseudo(settings.database_path, username)
    if not members:
        respond(
            blocks=build_error_blocks(
                title="Member not tracked",
                body=f"The Root-Me username `{username}` is not in the tracked member list.",
            ),
            response_type="ephemeral",
        )
        return

    if len(members) == 1:
        member = members[0]
        respond(
            blocks=build_remove_confirmation_blocks(member.id, member.rootme_pseudo, member.rootme_id),
            response_type="ephemeral",
        )
        return

    rootme_ids = [member.rootme_id for member in members if member.rootme_id is not None]
    try:
        profiles = asyncio.run(rootme_client.get_profiles_by_ids(rootme_ids))
    except RootMeAuthenticationError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me authentication failed",
                body="The configured `ROOTME_API_KEY` was rejected by Root-Me. Update the API key and restart the bot.",
            ),
            response_type="ephemeral",
        )
        return
    except RootMeApiError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me API unavailable",
                body="The Root-Me API is temporarily unavailable. Please try again in a few minutes.",
            ),
            response_type="ephemeral",
        )
        return

    respond(
        blocks=build_candidate_selection_blocks(
            title=":mag: Multiple tracked members found",
            body="More than one tracked member has that username. Choose which account to remove.",
            profiles=profiles,
            action_id="select_remove_member",
        ),
        response_type="ephemeral",
    )


def _search_profiles_or_respond(
    respond: Any,
    *,
    rootme_client: RootMeClient,
    username: str,
) -> list[RootMeProfile] | None:
    try:
        profiles = asyncio.run(rootme_client.search_profiles(username))
    except RootMeAuthenticationError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me authentication failed",
                body="The configured `ROOTME_API_KEY` was rejected by Root-Me. Update the API key and restart the bot.",
            ),
            response_type="ephemeral",
        )
        return None
    except RootMeRateLimitError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me rate limit reached",
                body="Root-Me is temporarily rate limiting requests. Wait a bit and try the command again.",
            ),
            response_type="ephemeral",
        )
        return None
    except RootMeApiError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me API unavailable",
                body="The Root-Me API is temporarily unavailable. Please try again in a few minutes.",
            ),
            response_type="ephemeral",
        )
        return None

    if not profiles:
        respond(
            blocks=build_error_blocks(
                title="Profile not found",
                body=f"The Root-Me username `{username}` was not found. Check the spelling and try again.",
            ),
            response_type="ephemeral",
        )
        return None
    return profiles


def _persist_selected_profile(
    respond: Any,
    *,
    settings: Settings,
    profile: RootMeProfile,
    added_by: str | None,
) -> None:
    try:
        add_member(
            settings.database_path,
            rootme_pseudo=profile.username,
            rootme_id=profile.id,
            added_by=added_by,
        )
    except MemberAlreadyExistsError:
        respond(
            blocks=build_error_blocks(
                title="Member already tracked",
                body=f"The Root-Me account `{profile.username}` with ID `{profile.id}` is already in the tracked member list.",
            ),
            response_type="ephemeral",
        )
        return

    respond(blocks=build_member_added_blocks(profile), response_type="in_channel")


def _build_rootme_client(settings: Settings) -> RootMeClient:
    return RootMeClient(
        api_key=settings.rootme_api_key,
        base_url=settings.rootme_api_base_url,
        request_delay_ms=settings.rootme_request_delay_ms,
        timeout_seconds=settings.rootme_timeout_seconds,
    )
