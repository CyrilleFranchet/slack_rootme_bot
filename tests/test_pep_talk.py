from datetime import UTC, datetime

import httpx

from services.pep_talk import OllamaPepTalkService
from services.rootme_client import ChallengeResolution, RootMeProfile


def _build_profile() -> RootMeProfile:
    return RootMeProfile(
        id=42,
        username="alice",
        score=2450,
        rootme_rank="1203",
        rootme_position=4521,
        challenges_count=385,
        profile_url="https://www.root-me.org/alice",
        categories=(),
        recent_resolutions=(),
        fetched_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )


def test_build_message_uses_fallback_when_ollama_is_disabled() -> None:
    service = OllamaPepTalkService(
        base_url="http://127.0.0.1:11434",
        model=None,
        timeout_seconds=5.0,
    )

    message = service.build_message(
        profile=_build_profile(),
        recent_resolutions=[ChallengeResolution(title="JWT - Revoked token", validated_at="2026-03-11")],
    )

    assert message


def test_build_message_returns_ollama_response(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, path: str, json: dict) -> httpx.Response:
            request = httpx.Request("POST", f"http://127.0.0.1:11434{path}")
            return httpx.Response(
                200,
                json={"response": "That challenge just got socially engineered by skill."},
                request=request,
            )

    monkeypatch.setattr("services.pep_talk.httpx.Client", FakeClient)

    service = OllamaPepTalkService(
        base_url="http://127.0.0.1:11434",
        model="qwen2.5:0.5b",
        timeout_seconds=5.0,
    )

    message = service.build_message(
        profile=_build_profile(),
        recent_resolutions=[ChallengeResolution(title="JWT - Revoked token", validated_at="2026-03-11")],
    )

    assert message == "That challenge just got socially engineered by skill."


def test_build_message_falls_back_on_ollama_failure(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, path: str, json: dict) -> httpx.Response:
            raise httpx.ConnectError("boom")

    monkeypatch.setattr("services.pep_talk.httpx.Client", FakeClient)

    service = OllamaPepTalkService(
        base_url="http://127.0.0.1:11434",
        model="qwen2.5:0.5b",
        timeout_seconds=5.0,
    )

    message = service.build_message(
        profile=_build_profile(),
        recent_resolutions=[ChallengeResolution(title="JWT - Revoked token", validated_at="2026-03-11")],
    )

    assert message
