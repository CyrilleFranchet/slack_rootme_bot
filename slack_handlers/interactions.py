from __future__ import annotations

import json
from typing import Any

from slack_bolt import App

from config import Settings
from db.models import MemberNotFoundError, delete_member
from utils.formatter import (
    build_error_blocks,
    build_member_removed_blocks,
    build_remove_cancelled_blocks,
)


def register_interactions(app: App, settings: Settings) -> None:
    @app.action("confirm_remove_member")
    def handle_confirm_remove_member(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        rootme_pseudo = _extract_rootme_pseudo(body)
        if not rootme_pseudo:
            respond(
                blocks=build_error_blocks(
                    title="Invalid action payload",
                    body="The removal request payload is missing the Root-Me username.",
                ),
                replace_original=False,
                response_type="ephemeral",
            )
            return

        try:
            removed_member = delete_member(settings.database_path, rootme_pseudo)
        except MemberNotFoundError:
            respond(
                blocks=build_error_blocks(
                    title="Member not tracked",
                    body=f"The Root-Me username `{rootme_pseudo}` is no longer in the tracked member list.",
                ),
                replace_original=True,
                response_type="ephemeral",
            )
            return

        respond(
            blocks=build_member_removed_blocks(removed_member.rootme_pseudo),
            replace_original=True,
            response_type="ephemeral",
        )

    @app.action("cancel_remove_member")
    def handle_cancel_remove_member(ack: Any, body: dict[str, Any], respond: Any) -> None:
        ack()
        rootme_pseudo = _extract_rootme_pseudo(body) or "this member"
        respond(
            blocks=build_remove_cancelled_blocks(rootme_pseudo),
            replace_original=True,
            response_type="ephemeral",
        )


def _extract_rootme_pseudo(body: dict[str, Any]) -> str | None:
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

    rootme_pseudo = payload.get("rootme_pseudo")
    if isinstance(rootme_pseudo, str) and rootme_pseudo.strip():
        return rootme_pseudo.strip()
    return None
