from services.rootme_client import RootMeClient


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
    assert profile.global_rank == 1203
    assert profile.challenges_count == 3
    assert profile.categories[0].name == "Cracking"


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
    assert client._candidate_matches_username(candidates[0], "alice")
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
