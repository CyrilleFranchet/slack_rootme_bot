from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import math
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class RootMeApiError(Exception):
    """Raised when the Root-Me API cannot satisfy a request."""


class RootMeAuthenticationError(RootMeApiError):
    """Raised when the Root-Me API key is missing or invalid."""


class RootMeRateLimitError(RootMeApiError):
    """Raised when the Root-Me API rate limit has been exceeded."""


class RootMeUserNotFoundError(RootMeApiError):
    """Raised when a Root-Me username cannot be found."""


@dataclass(frozen=True)
class CategoryProgress:
    name: str
    completed: int
    total: int | None = None


@dataclass(frozen=True)
class RootMeProfile:
    id: int
    username: str
    score: int
    global_rank: int | None
    challenges_count: int
    profile_url: str
    categories: tuple[CategoryProgress, ...]
    fetched_at: datetime


class RootMeClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        request_delay_ms: int,
        timeout_seconds: float,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._request_delay_seconds = max(request_delay_ms, 0) / 1000
        self._timeout = timeout_seconds
        self._rate_limit_lock = asyncio.Lock()
        self._next_request_time = 0.0

    async def get_profile(self, username: str) -> RootMeProfile:
        matches = await self.search_profiles(username)
        if not matches:
            raise RootMeUserNotFoundError(
                f"The Root-Me username `{username}` could not be found."
            )
        if len(matches) > 1:
            raise RootMeApiError(
                f"The Root-Me username `{username}` matched multiple accounts."
            )
        return matches[0]

    async def get_profile_by_id(self, author_id: int) -> RootMeProfile:
        author_payload = await self._request_json(f"/auteurs/{author_id}")
        validations_payload = await self._request_json(f"/auteurs/{author_id}/validations")
        author = self._unwrap_object(author_payload)
        fallback_username = self._pick_str(author, "nom", "name", default=str(author_id)) or str(author_id)
        return self._build_profile(
            author_payload,
            validations_payload=validations_payload,
            fallback_username=fallback_username,
        )

    async def get_profiles_by_ids(self, author_ids: list[int]) -> list[RootMeProfile]:
        profiles = await asyncio.gather(*(self.get_profile_by_id(author_id) for author_id in author_ids))
        return list(profiles)

    async def search_profiles(self, username: str) -> list[RootMeProfile]:
        candidate_ids = await self._search_exact_candidate_ids(username)
        if not candidate_ids:
            return []

        profiles = await self.get_profiles_by_ids(candidate_ids)
        return [profile for profile in profiles if profile.username == username]

    async def _search_exact_candidate_ids(self, username: str) -> list[int]:
        candidate_ids: list[int] = []
        seen_ids: set[int] = set()
        next_path: str | None = "/auteurs"
        next_params: dict[str, Any] | None = {"nom": username}

        while next_path is not None:
            payload = await self._request_json(next_path, params=next_params)
            for candidate in self._extract_search_candidates(payload):
                candidate_name = self._pick_str(
                    candidate,
                    "nom",
                    "name",
                    "titre",
                    "title",
                    "pseudo",
                    "login",
                )
                candidate_id = self._pick_candidate_id(candidate)
                if candidate_id is None or candidate_name is None or candidate_id in seen_ids:
                    continue
                if candidate_name != username:
                    continue
                seen_ids.add(candidate_id)
                candidate_ids.append(candidate_id)

            next_href = self._extract_next_href(payload)
            if next_href:
                next_path = next_href
                next_params = None
            else:
                next_path = None
                next_params = None

        return candidate_ids

    async def _request_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        attempts = 3
        backoff_seconds = 1.0

        for attempt in range(1, attempts + 1):
            await self._wait_for_rate_limit()
            try:
                async with httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout,
                    headers={
                        "Cookie": f"api_key={self._api_key}",
                        "Accept": "application/json",
                    },
                ) as client:
                    response = await client.get(path, params=params)

                if response.status_code == 404:
                    raise RootMeUserNotFoundError("The requested Root-Me resource was not found.")
                if response.status_code in {401, 403}:
                    raise RootMeAuthenticationError(
                        "The Root-Me API rejected the configured API key."
                    )
                if response.status_code == 429:
                    raise RootMeRateLimitError(
                        "The Root-Me API rate limit has been reached."
                    )
                if response.status_code in {500, 502, 503, 504}:
                    raise RootMeApiError(
                        f"Transient Root-Me API error ({response.status_code})."
                    )
                if response.is_error:
                    logger.warning(
                        "Unexpected Root-Me API response",
                        extra={
                            "status_code": response.status_code,
                            "path": path,
                            "response_text": response.text[:500],
                        },
                    )
                    raise RootMeApiError(
                        f"Unexpected Root-Me API response ({response.status_code})."
                    )

                return response.json()
            except RootMeUserNotFoundError:
                raise
            except RootMeAuthenticationError:
                raise
            except RootMeRateLimitError as exc:
                logger.warning(
                    "Root-Me API rate limit reached",
                    extra={"path": path, "attempt": attempt, "error": str(exc)},
                )
                if attempt == attempts:
                    raise RootMeRateLimitError(
                        "The Root-Me API rate limit has been reached. Please try again shortly."
                    ) from exc
                await asyncio.sleep(backoff_seconds * 3)
                backoff_seconds *= 2
            except (httpx.HTTPError, RootMeApiError) as exc:
                logger.warning(
                    "Root-Me API request failed",
                    extra={"path": path, "attempt": attempt, "error": str(exc)},
                )
                if attempt == attempts:
                    raise RootMeApiError(
                        "The Root-Me API is temporarily unavailable."
                    ) from exc
                await asyncio.sleep(backoff_seconds)
                backoff_seconds *= 2

        raise RootMeApiError("The Root-Me API is temporarily unavailable.")

    async def _wait_for_rate_limit(self) -> None:
        async with self._rate_limit_lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            if now < self._next_request_time:
                await asyncio.sleep(self._next_request_time - now)
                now = loop.time()
            self._next_request_time = now + self._request_delay_seconds

    def _build_profile(
        self,
        author_payload: Any,
        *,
        validations_payload: Any,
        fallback_username: str,
    ) -> RootMeProfile:
        author = self._unwrap_object(author_payload)
        validations = self._extract_items(validations_payload)

        username = self._pick_str(author, "nom", "name", default=fallback_username)
        author_id = self._pick_int(author, "id", "id_auteur")
        if author_id is None:
            raise RootMeApiError("The Root-Me API response did not include an author ID.")

        profile_url = self._pick_str(
            author,
            "url",
            "lien",
            "profile_url",
            default=f"https://www.root-me.org/{username}",
        )
        score = self._pick_int(author, "score", default=0) or 0
        global_rank = self._pick_int(author, "position", "rang", "rank")
        validations_count = self._count_validations(author, validations)
        categories = self._extract_categories(author)

        return RootMeProfile(
            id=author_id,
            username=username,
            score=score,
            global_rank=global_rank,
            challenges_count=validations_count,
            profile_url=profile_url,
            categories=tuple(categories),
            fetched_at=datetime.now(UTC),
        )

    def _count_validations(self, author: dict[str, Any], validations: list[Any]) -> int:
        direct_count = self._pick_int(
            author,
            "nb_validations",
            "validations_count",
            "challenges_count",
        )
        if direct_count is not None:
            return direct_count

        nested = author.get("validations")
        if isinstance(nested, list):
            return len(nested)
        if isinstance(nested, int):
            return nested

        return len(validations)

    def _extract_categories(self, author: dict[str, Any]) -> list[CategoryProgress]:
        categories_payload = author.get("categories") or author.get("stats") or []
        if isinstance(categories_payload, dict):
            categories_payload = list(categories_payload.values())
        if not isinstance(categories_payload, list):
            return []

        categories: list[CategoryProgress] = []
        for item in categories_payload:
            if not isinstance(item, dict):
                continue
            name = self._pick_str(item, "nom", "name", "titre")
            completed = self._pick_int(item, "validations", "count", "completed", default=0)
            total = self._pick_int(item, "total", "total_challenges", "available")
            if name is None:
                continue
            categories.append(
                CategoryProgress(name=name, completed=completed or 0, total=total)
            )

        categories.sort(key=lambda item: item.completed, reverse=True)
        return categories[:8]

    @staticmethod
    def _extract_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("items", "data", "auteurs", "children"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            if all(not isinstance(value, (list, dict)) for value in payload.values()):
                return [payload]
        return []

    def _extract_search_candidates(self, payload: Any) -> list[dict[str, Any]]:
        seen: set[int] = set()
        candidates: list[dict[str, Any]] = []

        for item in self._walk_dicts(payload):
            if self._pick_candidate_id(item) is None:
                continue
            if self._pick_str(
                item,
                "nom",
                "name",
                "titre",
                "title",
                "pseudo",
                "login",
            ) is None:
                continue

            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            candidates.append(item)

        return candidates

    def _extract_next_href(self, payload: Any) -> str | None:
        link_objects = self._extract_link_objects(payload)
        for link in link_objects:
            rel = self._pick_str(link, "rel")
            href = self._pick_str(link, "href", "url")
            if rel == "next" and href is not None:
                return href
        return None

    def _extract_link_objects(self, payload: Any) -> list[dict[str, Any]]:
        links: list[dict[str, Any]] = []
        for item in self._walk_dicts(payload):
            if self._pick_str(item, "rel") and self._pick_str(item, "href", "url"):
                links.append(item)
        return links

    def _pick_candidate_id(self, payload: dict[str, Any]) -> int | None:
        candidate_id = self._pick_int(payload, "id", "id_auteur", "auteur", "author_id", "user_id")
        if candidate_id is not None:
            return candidate_id

        nested_author = payload.get("auteur") or payload.get("author") or payload.get("user")
        if isinstance(nested_author, dict):
            return self._pick_int(
                nested_author,
                "id",
                "id_auteur",
                "auteur",
                "author_id",
                "user_id",
            )
        return None

    @classmethod
    def _walk_dicts(cls, payload: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        if isinstance(payload, dict):
            found.append(payload)
            for value in payload.values():
                found.extend(cls._walk_dicts(value))
        elif isinstance(payload, list):
            for item in payload:
                found.extend(cls._walk_dicts(item))
        return found

    @staticmethod
    def _unwrap_object(payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            for key in ("data", "auteur", "item"):
                value = payload.get(key)
                if isinstance(value, dict):
                    return value
            return payload
        raise RootMeApiError("Unexpected Root-Me API response format.")

    @staticmethod
    def _pick_str(payload: dict[str, Any], *keys: str, default: str | None = None) -> str | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return default

    @staticmethod
    def _pick_int(payload: dict[str, Any], *keys: str, default: int | None = None) -> int | None:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return math.floor(value)
            if isinstance(value, str):
                normalized = value.replace(" ", "").replace("#", "").replace(",", "")
                if normalized.isdigit():
                    return int(normalized)
        return default
