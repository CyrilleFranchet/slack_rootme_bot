from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from slack_bolt import App

from config import Settings
from db.models import list_members
from services.ranking import build_ranking
from services.rootme_client import (
    RootMeApiError,
    RootMeAuthenticationError,
    RootMeClient,
    RootMeUserNotFoundError,
)
from utils.formatter import (
    build_empty_ranking_blocks,
    build_error_blocks,
    build_help_blocks,
    build_profile_blocks,
    build_ranking_blocks,
)


SUPPORTED_SUBCOMMANDS = {
    "help",
    "aide",
    "ranking",
    "classement",
    "profile",
    "profil",
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
                rootme_client=_build_rootme_client(settings),
            )
            return

        if subcommand in {"profile", "profil"}:
            ack(text="Fetching the Root-Me profile...")
            username = " ".join(parts[1:]).strip()
            _handle_profile_command(
                respond,
                rootme_client=_build_rootme_client(settings),
                username=username,
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
    rootme_client: RootMeClient,
) -> None:
    members = list_members(settings.database_path)
    if not members:
        respond(blocks=build_empty_ranking_blocks(), response_type="ephemeral")
        return

    try:
        profiles = asyncio.run(
            rootme_client.get_profiles([member.rootme_pseudo for member in members])
        )
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

    try:
        profile = asyncio.run(rootme_client.get_profile(username))
    except RootMeUserNotFoundError:
        respond(
            blocks=build_error_blocks(
                title="Profile not found",
                body=f"The Root-Me username `{username}` was not found. Check the spelling and try again.",
            ),
            response_type="ephemeral",
        )
        return
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

    respond(blocks=build_profile_blocks(profile), response_type="ephemeral")


def _build_rootme_client(settings: Settings) -> RootMeClient:
    return RootMeClient(
        api_key=settings.rootme_api_key,
        base_url=settings.rootme_api_base_url,
        request_delay_ms=settings.rootme_request_delay_ms,
        timeout_seconds=settings.rootme_timeout_seconds,
    )
