from __future__ import annotations

from typing import Any

from slack_bolt import App

from utils.formatter import build_help_blocks


SUPPORTED_SUBCOMMANDS = {"help"}


def register_commands(app: App) -> None:
    @app.command("/rootme")
    def handle_rootme_command(ack: Any, respond: Any, command: dict[str, Any]) -> None:
        ack()

        text = (command.get("text") or "").strip()
        subcommand = text.split()[0].lower() if text else "help"

        if subcommand == "help":
            respond(blocks=build_help_blocks(), response_type="ephemeral")
            return

        respond(
            text=(
                f"Unknown subcommand `{subcommand}`. "
                "Use `/rootme help` to see the available commands."
            ),
            blocks=build_help_blocks(
                title="Unknown subcommand",
                body=(
                    f"`{subcommand}` is not supported yet in M1. "
                    "Use `/rootme help` to view the current command set."
                ),
            ),
            response_type="ephemeral",
        )
