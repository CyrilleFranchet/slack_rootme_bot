from services.rootme_client import RootMeClient


def test_build_profile_parses_author_and_validations_payloads() -> None:
    client = RootMeClient(
        api_key="test",
        base_url="https://api.root-me.org",
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
