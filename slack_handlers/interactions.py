from __future__ import annotations

import asyncio
import json
from typing import Any

from slack_bolt import App

from config import Settings
from db.models import (
    MemberAlreadyExistsError,
    MemberNotFoundError,
    add_member,
    delete_member,
    get_member_by_rootme_id,
)
from services.rootme_client import (
    RootMeApiError,
    RootMeAuthenticationError,
    RootMeClient,
    RootMeRateLimitError,
)
from utils.formatter import (
    build_error_blocks,
    build_member_added_blocks,
    build_member_removed_blocks,
    build_profile_blocks,
    build_remove_cancelled_blocks,
    build_remove_confirmation_blocks,
)


def register_interactions(app: App, settings: Settings) -> None:
    @app.action("select_profile_candidate")
    def handle_select_profile_candidate(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        rootme_id = _extract_int_payload(body, "rootme_id")
        if rootme_id is None:
            _respond_invalid_payload(respond)
            return

        profile = _fetch_profile_or_respond(
            respond,
            settings=settings,
            rootme_id=rootme_id,
            replace_original=True,
        )
        if profile is None:
            return

        respond(blocks=build_profile_blocks(profile), replace_original=True, response_type="ephemeral")

    @app.action("select_add_member")
    def handle_select_add_member(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        rootme_id = _extract_int_payload(body, "rootme_id")
        if rootme_id is None:
            _respond_invalid_payload(respond)
            return

        profile = _fetch_profile_or_respond(
            respond,
            settings=settings,
            rootme_id=rootme_id,
            replace_original=True,
        )
        if profile is None:
            return

        if get_member_by_rootme_id(settings.database_path, profile.id) is not None:
            respond(
                blocks=build_error_blocks(
                    title="Member already tracked",
                    body=f"The Root-Me account `{profile.username}` with ID `{profile.id}` is already in the tracked member list.",
                ),
                replace_original=True,
                response_type="ephemeral",
            )
            return

        try:
            add_member(
                settings.database_path,
                rootme_pseudo=profile.username,
                rootme_id=profile.id,
                added_by=_extract_slack_user_id(body),
            )
        except MemberAlreadyExistsError:
            respond(
                blocks=build_error_blocks(
                    title="Member already tracked",
                    body=f"The Root-Me account `{profile.username}` with ID `{profile.id}` is already in the tracked member list.",
                ),
                replace_original=True,
                response_type="ephemeral",
            )
            return

        respond(
            blocks=build_member_added_blocks(profile),
            replace_original=True,
            response_type="in_channel",
        )

    @app.action("select_remove_member")
    def handle_select_remove_member(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        rootme_id = _extract_int_payload(body, "rootme_id")
        if rootme_id is None:
            _respond_invalid_payload(respond)
            return

        member = get_member_by_rootme_id(settings.database_path, rootme_id)
        if member is None:
            respond(
                blocks=build_error_blocks(
                    title="Member not tracked",
                    body=f"The Root-Me account with ID `{rootme_id}` is no longer in the tracked member list.",
                ),
                replace_original=True,
                response_type="ephemeral",
            )
            return

        respond(
            blocks=build_remove_confirmation_blocks(member.id, member.rootme_pseudo, member.rootme_id),
            replace_original=True,
            response_type="ephemeral",
        )

    @app.action("confirm_remove_member")
    def handle_confirm_remove_member(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        member_id = _extract_int_payload(body, "member_id")
        if member_id is None:
            _respond_invalid_payload(respond)
            return

        try:
            removed_member = delete_member(settings.database_path, member_id)
        except MemberNotFoundError:
            respond(
                blocks=build_error_blocks(
                    title="Member not tracked",
                    body=f"The tracked member with ID `{member_id}` is no longer in the tracked member list.",
                ),
                replace_original=True,
                response_type="ephemeral",
            )
            return

        respond(
            blocks=build_member_removed_blocks(removed_member.rootme_pseudo, removed_member.rootme_id),
            replace_original=True,
            response_type="ephemeral",
        )

    @app.action("cancel_remove_member")
    def handle_cancel_remove_member(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        rootme_pseudo = _extract_str_payload(body, "rootme_pseudo") or "this member"
        rootme_id = _extract_int_payload(body, "rootme_id")
        respond(
            blocks=build_remove_cancelled_blocks(rootme_pseudo, rootme_id),
            replace_original=True,
            response_type="ephemeral",
        )


def _fetch_profile_or_respond(
    respond: Any,
    *,
    settings: Settings,
    rootme_id: int,
    replace_original: bool,
):
    client = RootMeClient(
        api_key=settings.rootme_api_key,
        base_url=settings.rootme_api_base_url,
        request_delay_ms=settings.rootme_request_delay_ms,
        timeout_seconds=settings.rootme_timeout_seconds,
    )
    try:
        return asyncio.run(client.get_profile_by_id(rootme_id))
    except RootMeAuthenticationError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me authentication failed",
                body="The configured `ROOTME_API_KEY` was rejected by Root-Me. Update the API key and restart the bot.",
            ),
            replace_original=replace_original,
            response_type="ephemeral",
        )
    except RootMeRateLimitError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me rate limit reached",
                body="Root-Me is temporarily rate limiting requests. Wait a bit and try again.",
            ),
            replace_original=replace_original,
            response_type="ephemeral",
        )
    except RootMeApiError:
        respond(
            blocks=build_error_blocks(
                title="Root-Me API unavailable",
                body="The Root-Me API is temporarily unavailable. Please try again in a few minutes.",
            ),
            replace_original=replace_original,
            response_type="ephemeral",
        )
    return None


def _respond_invalid_payload(respond: Any) -> None:
    respond(
        blocks=build_error_blocks(
            title="Invalid action payload",
            body="The interactive request payload is missing the required selection data.",
        ),
        replace_original=False,
        response_type="ephemeral",
    )


def _extract_payload(body: dict[str, Any]) -> dict[str, Any] | None:
    actions = body.get("actions")
    if not isinstance(actions, list) or not actions:
        return None

    action = actions[0]
    if not isinstance(action, dict):
        return None

    raw_value = action.get("value")
    if not isinstance(raw_value, str):
        return None

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _extract_int_payload(body: dict[str, Any], key: str) -> int | None:
    payload = _extract_payload(body)
    if payload is None:
        return None

    value = payload.get(key)
    if isinstance(value, int):
        return value
    return None


def _extract_str_payload(body: dict[str, Any], key: str) -> str | None:
    payload = _extract_payload(body)
    if payload is None:
        return None

    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _extract_slack_user_id(body: dict[str, Any]) -> str | None:
    user = body.get("user")
    if not isinstance(user, dict):
        return None
    user_id = user.get("id")
    if isinstance(user_id, str) and user_id.strip():
        return user_id.strip()
    return None
