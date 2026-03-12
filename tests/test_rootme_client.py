from services.rootme_client import RootMeClient, RootMeRateLimitError


def test_build_profile_parses_author_and_validations_payloads() -> None:
    client = RootMeClient(
        api_key="test",
        base_url="https://api.www.root-me.org",
        request_delay_ms=0,
        timeout_seconds=10,
    )

    profile = client._build_profile(
        {
            "id": 42,
            "nom": "alice",
            "score": "2450",
            "position": "1203",
            "rang": "999",
            "url": "https://www.root-me.org/alice",
            "categories": [
                {"nom": "Web", "validations": 38, "total": 45},
                {"nom": "Cracking", "validations": 42, "total": 50},
            ],
        },
        validations_payload={
            "items": [
                {"id_challenge": 1},
                {"id_challenge": 2},
                {"id_challenge": 3},
            ]
        },
        fallback_username="alice",
    )

    assert profile.username == "alice"
    assert profile.score == 2450
    assert profile.rootme_rank == "999"
    assert profile.rootme_position == 1203
    assert profile.challenges_count == 3
    assert profile.categories[0].name == "Cracking"
    assert len(profile.recent_resolutions) == 3


def test_build_profile_keeps_rang_and_position_separate() -> None:
    client = RootMeClient(
        api_key="test",
        base_url="https://api.www.root-me.org",
        request_delay_ms=0,
        timeout_seconds=10,
    )

    profile = client._build_profile(
        {
            "id": 42,
            "nom": "alice",
            "score": "2450",
            "position": "1203",
            "rang": "999",
            "url": "https://www.root-me.org/alice",
        },
        validations_payload={"items": []},
        fallback_username="alice",
    )

    assert profile.rootme_rank == "999"
    assert profile.rootme_position == 1203


def test_build_profile_supports_string_rank_labels() -> None:
    client = RootMeClient(
        api_key="test",
        base_url="https://api.www.root-me.org",
        request_delay_ms=0,
        timeout_seconds=10,
    )

    profile = client._build_profile(
        {
            "id": 8466,
            "nom": "kyr1ll0s",
            "score": "3345",
            "position": 3016,
            "rang": "insider",
            "url": "https://www.root-me.org/kyr1ll0s",
        },
        validations_payload={"items": []},
        fallback_username="kyr1ll0s",
    )

    assert profile.rootme_rank == "insider"
    assert profile.rootme_position == 3016


def test_extract_search_candidates_handles_nested_search_payload() -> None:
    client = RootMeClient(
        api_key="test",
        base_url="https://api.www.root-me.org",
        request_delay_ms=0,
        timeout_seconds=10,
    )

    candidates = client._extract_search_candidates(
        {
            "metadata": {"page": 1},
            "data": {
                "items": [
                    {
                        "title": "alice",
                        "author": {"id": 42},
                    }
                ]
            },
        }
    )

    assert len(candidates) == 1
    assert client._pick_candidate_id(candidates[0]) == 42


def test_extract_search_candidates_preserves_duplicate_usernames() -> None:
    client = RootMeClient(
        api_key="test",
        base_url="https://api.www.root-me.org",
        request_delay_ms=0,
        timeout_seconds=10,
    )

    candidates = client._extract_search_candidates(
        {
            "items": [
                {"nom": "alice", "id": 1},
                {"nom": "alice", "id": 2},
            ]
        }
    )

    assert len(candidates) == 2
    assert [client._pick_candidate_id(candidate) for candidate in candidates] == [1, 2]


def test_extract_next_href_from_paginated_search_payload() -> None:
    client = RootMeClient(
        api_key="test",
        base_url="https://api.www.root-me.org",
        request_delay_ms=0,
        timeout_seconds=10,
    )

    payload = [
        {
            "0": {"id_auteur": "2882", "nom": "phil"},
            "1": {"id_auteur": "3788", "nom": "Phil"},
        },
        {"rel": "next", "href": "https://api.www.root-me.org/auteurs?nom=Phil&debut_auteurs=50"},
    ]

    assert client._extract_next_href(payload) == "https://api.www.root-me.org/auteurs?nom=Phil&debut_auteurs=50"


def test_rate_limit_error_type_is_available() -> None:
    error = RootMeRateLimitError("rate limited")

    assert str(error) == "rate limited"


def test_search_exact_candidate_ids_keeps_only_exact_matches_across_pages() -> None:
    client = RootMeClient(
        api_key="test",
        base_url="https://api.www.root-me.org",
        request_delay_ms=0,
        timeout_seconds=10,
    )

    async def fake_request_json(path: str, *, params=None):
        if path == "/auteurs":
            return [
                {
                    "0": {"id_auteur": "2882", "nom": "phil"},
                    "1": {"id_auteur": "3788", "nom": "Phil"},
                    "2": {"id_auteur": "4396", "nom": "philippe"},
                },
                {"rel": "next", "href": "https://api.www.root-me.org/auteurs?nom=Phil&debut_auteurs=50"},
            ]
        return [
            {
                "0": {"id_auteur": "24870", "nom": "Phil"},
                "1": {"id_auteur": "42613", "nom": "Phil"},
                "2": {"id_auteur": "58958", "nom": "Philippe Ed"},
            }
        ]

    client._request_json = fake_request_json  # type: ignore[method-assign]

    import asyncio

    candidate_ids = asyncio.run(client._search_exact_candidate_ids("Phil"))

    assert candidate_ids == [3788, 24870, 42613]
