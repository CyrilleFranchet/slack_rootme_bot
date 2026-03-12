from __future__ import annotations

from typing import Any


def build_help_blocks(
    *,
    title: str = "Root-Me Slack Bot",
    body: str = "Available commands for the current milestone.",
) -> list[dict[str, Any]]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":shield: Root-Me Slack Bot"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{title}*\n{body}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*`/rootme help`*\n"
                    "Show the list of supported commands and usage examples."
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "Planned next: `/rootme ranking`, `/rootme profile <username>`, "
                        "`/rootme add <username>`, and `/rootme remove <username>`."
                    ),
                }
            ],
        },
    ]
