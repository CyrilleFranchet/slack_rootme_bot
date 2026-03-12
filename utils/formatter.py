from __future__ import annotations

from datetime import datetime
import json
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
                    "Show details for a specific Root-Me profile.\n\n"
                    "*`/rootme add <rootme_id>`*\n"
                    "Fetch a Root-Me profile by ID, then ask for confirmation before tracking it.\n\n"
                    "*`/rootme list`*\n"
                    "Show the tracked members and who added them.\n\n"
                    "*`/rootme remove <username>`*\n"
                    "Ask for confirmation, then remove a tracked member."
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "Aliases: `/rootme aide`, `/rootme classement`, `/rootme profil <username>`, "
                        "`/rootme ajouter <rootme_id>`, `/rootme liste`, and `/rootme supprimer <username>`."
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
                    "Use `/rootme add <rootme_id>` to start tracking someone."
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
    recent_resolution_lines = _format_recent_resolutions(profile)
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

    if recent_resolution_lines:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Latest challenge solves*\n" + "\n".join(recent_resolution_lines),
                },
            }
        )

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


def build_member_added_blocks(profile: RootMeProfile) -> list[dict[str, Any]]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":white_check_mark: Member added"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{profile.username}* is now tracked.\n"
                    f"Root-Me ID: `{profile.id}`\n"
                    f"Score: {profile.score:,} pts\n"
                    f"Global rank: {_format_global_rank(profile.global_rank)}"
                ),
            },
        },
    ]


def build_member_list_blocks(members: list[dict[str, str]]) -> list[dict[str, Any]]:
    if not members:
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": ":busts_in_silhouette: Tracked members"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No Root-Me members are currently tracked.",
                },
            },
        ]

    lines = [
        f"*{member['rootme_pseudo']}*  |  ID `{member['rootme_id']}`  |  added by {member['added_by']}"
        for member in members
    ]
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":busts_in_silhouette: Tracked members"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        },
    ]


def build_add_confirmation_blocks(profile: RootMeProfile) -> list[dict[str, Any]]:
    payload = json.dumps({"rootme_id": profile.id})
    blocks = build_profile_blocks(profile)
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Add member"},
                    "style": "primary",
                    "action_id": "confirm_add_member",
                    "value": payload,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Cancel"},
                    "action_id": "cancel_add_member",
                    "value": payload,
                },
            ],
        }
    )
    return blocks


def build_add_cancelled_blocks(rootme_id: int | None) -> list[dict[str, Any]]:
    suffix = f" for Root-Me ID `{rootme_id}`" if rootme_id is not None else ""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":information_source: Add request cancelled{suffix}.",
            },
        }
    ]


def build_candidate_selection_blocks(
    *,
    title: str,
    body: str,
    profiles: list[RootMeProfile],
    action_id: str,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": title},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": body},
        },
    ]

    for profile in profiles:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{profile.username}*  |  ID `{profile.id}`\n"
                        f"{_format_global_rank(profile.global_rank)}  |  "
                        f"{profile.challenges_count:,} challenges  |  {profile.score:,} pts"
                    ),
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Choose"},
                    "action_id": action_id,
                    "value": json.dumps({"rootme_id": profile.id}),
                },
            }
        )

    return blocks


def build_remove_confirmation_blocks(member_id: int, rootme_pseudo: str, rootme_id: int | None) -> list[dict[str, Any]]:
    payload = json.dumps(
        {"member_id": member_id, "rootme_pseudo": rootme_pseudo, "rootme_id": rootme_id}
    )
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":warning: Confirm member removal"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"Remove *{rootme_pseudo}*"
                    + (f" (Root-Me ID `{rootme_id}`)" if rootme_id is not None else "")
                    + " from the tracked Root-Me members?"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Remove"},
                    "style": "danger",
                    "action_id": "confirm_remove_member",
                    "value": payload,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Cancel"},
                    "action_id": "cancel_remove_member",
                    "value": payload,
                },
            ],
        },
    ]


def build_member_removed_blocks(rootme_pseudo: str, rootme_id: int | None) -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":wastebasket: *{rootme_pseudo}*"
                    + (f" (Root-Me ID `{rootme_id}`)" if rootme_id is not None else "")
                    + " is no longer tracked."
                ),
            },
        }
    ]


def build_remove_cancelled_blocks(rootme_pseudo: str, rootme_id: int | None) -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":information_source: Removal cancelled for *{rootme_pseudo}*"
                    + (f" (Root-Me ID `{rootme_id}`)" if rootme_id is not None else "")
                    + "."
                ),
            },
        }
    ]


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


def _format_recent_resolutions(profile: RootMeProfile) -> list[str]:
    lines: list[str] = []
    for resolution in profile.recent_resolutions:
        if resolution.validated_at:
            lines.append(f"- {resolution.validated_at}: {resolution.title}")
        else:
            lines.append(f"- {resolution.title}")
    return lines
