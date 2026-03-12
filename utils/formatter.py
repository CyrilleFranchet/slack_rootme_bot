from __future__ import annotations

from datetime import datetime
from typing import Any

from services.ranking import RankingEntry
from services.rootme_client import CategoryProgress, RootMeProfile


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
                    "Show the list of supported commands and usage examples.\n\n"
                    "*`/rootme ranking`*\n"
                    "Show the tracked-member leaderboard.\n\n"
                    "*`/rootme profile <username>`*\n"
                    "Show details for a specific Root-Me profile."
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "Aliases: `/rootme classement` and `/rootme profil <username>`. "
                        "Planned next: `/rootme add <username>` and `/rootme remove <username>`."
                    ),
                }
            ],
        },
    ]


def build_error_blocks(*, title: str, body: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":warning: Root-Me Bot"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{title}*\n{body}"},
        },
    ]


def build_empty_ranking_blocks() -> list[dict[str, Any]]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":trophy: Root-Me Ranking"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "No tracked members are stored yet. "
                    "M3 will add slash commands for managing the member list."
                ),
            },
        },
    ]


def build_ranking_blocks(entries: list[RankingEntry], *, updated_at: datetime) -> list[dict[str, Any]]:
    lines = [_format_ranking_line(entry) for entry in entries]
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":trophy: Root-Me Group Ranking"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Updated at {updated_at.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}",
                }
            ],
        },
    ]


def build_profile_blocks(profile: RootMeProfile) -> list[dict[str, Any]]:
    category_lines = _format_categories(profile.categories)
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f":bust_in_silhouette: Root-Me Profile: {profile.username}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Score*: {profile.score:,} pts\n"
                    f"*Global rank*: {_format_global_rank(profile.global_rank)}\n"
                    f"*Challenges solved*: {profile.challenges_count:,}\n"
                    f"*Profile*: {profile.profile_url}"
                ),
            },
        },
    ]

    if category_lines:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*By category*\n" + "\n".join(category_lines),
                },
            }
        )

    return blocks


def _format_ranking_line(entry: RankingEntry) -> str:
    medal = {1: ":first_place_medal:", 2: ":second_place_medal:", 3: ":third_place_medal:"}.get(
        entry.position,
        "•",
    )
    profile = entry.profile
    return (
        f"{medal} *{entry.position}. {profile.username}*"
        f" - {profile.score:,} pts"
        f" ({profile.challenges_count:,} challenges)"
        f" - {_format_global_rank(profile.global_rank)}"
    )


def _format_global_rank(rank: int | None) -> str:
    if rank is None:
        return "Unknown"
    return f"#{rank:,} worldwide"


def _format_categories(categories: tuple[CategoryProgress, ...]) -> list[str]:
    lines: list[str] = []
    for category in categories:
        progress = f"{category.completed:,}"
        if category.total is not None:
            progress = f"{progress}/{category.total:,}"
        lines.append(f"• *{category.name}*: {progress}")
    return lines
