from __future__ import annotations

import logging
import random
from typing import Final

import httpx

from services.rootme_client import ChallengeResolution, RootMeProfile


logger = logging.getLogger(__name__)

_FALLBACK_MESSAGES: Final[tuple[str, ...]] = (
    "Momentum is building. Keep the solves coming.",
    "Nice work. That challenge did not stand a chance.",
    "Another flag down. The leaderboard pressure is real.",
    "Clean solve. Time to queue up the next one.",
    "That is how streaks start. Keep pushing.",
)


class OllamaPepTalkService:
    def __init__(
        self,
        *,
        base_url: str,
        model: str | None,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model.strip() if model else None
        self._timeout_seconds = timeout_seconds

    @property
    def is_enabled(self) -> bool:
        return bool(self._model)

    def build_message(
        self,
        *,
        profile: RootMeProfile,
        recent_resolutions: list[ChallengeResolution],
    ) -> str:
        fallback_message = self._fallback_message(profile=profile, recent_resolutions=recent_resolutions)
        if not self.is_enabled:
            return fallback_message

        prompt = self._build_prompt(profile=profile, recent_resolutions=recent_resolutions)
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout_seconds) as client:
                response = client.post(
                    "/api/generate",
                    json={
                        "model": self._model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.9,
                        },
                    },
                )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            logger.warning(
                "Falling back to static solve message after Ollama generation failure",
                exc_info=True,
                extra={"username": profile.username},
            )
            return fallback_message

        candidate = payload.get("response")
        if not isinstance(candidate, str):
            return fallback_message

        normalized = " ".join(candidate.split())
        if not normalized:
            return fallback_message

        if len(normalized) > 160:
            normalized = normalized[:157].rstrip(" .,;:") + "..."

        return normalized

    def _build_prompt(
        self,
        *,
        profile: RootMeProfile,
        recent_resolutions: list[ChallengeResolution],
    ) -> str:
        solved_titles = ", ".join(resolution.title for resolution in recent_resolutions)
        return (
            "Write exactly one short sentence in American English for a Slack message. "
            "It should be either a light cybersecurity joke or an encouraging line. "
            "Keep it friendly, playful, non-cringey, and safe for work. "
            "Do not use hashtags, quotes, emojis, markdown, lists, or multiple sentences. "
            "Keep it under 22 words. "
            f"Root-Me username: {profile.username}. "
            f"Newly solved challenges: {solved_titles}."
        )

    def _fallback_message(
        self,
        *,
        profile: RootMeProfile,
        recent_resolutions: list[ChallengeResolution],
    ) -> str:
        seed = f"{profile.username}:{'|'.join(resolution.title for resolution in recent_resolutions)}"
        return random.Random(seed).choice(_FALLBACK_MESSAGES)
