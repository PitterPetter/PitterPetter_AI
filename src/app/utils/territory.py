"""Utilities for interacting with the Territory service."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import httpx

from config import TERRITORY_SERVICE_URL


class TerritoryServiceError(RuntimeError):
    """Raised when the territory service request or parsing fails."""


async def fetch_unlocked_districts(
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 5.0,
) -> List[Dict[str, Optional[str]]]:
    """
    Fetch the list of unlocked districts from the territory service.

    Returns a list of dicts with keys: id, name, city.
    """

    url = f"{TERRITORY_SERVICE_URL.rstrip('/')}/api/regions/search"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers or {})
    except httpx.RequestError as exc:
        raise TerritoryServiceError(f"Territory 서비스 연결 실패: {exc}") from exc

    if response.status_code != 200:
        raise TerritoryServiceError(
            f"Territory 서비스 응답 실패: {response.status_code} {response.text[:200]}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TerritoryServiceError("Territory 서비스 JSON 파싱 실패") from exc

    if not payload.get("success"):
        raise TerritoryServiceError("Territory 서비스 응답이 success=false")

    data = payload.get("data") or {}
    cities = data.get("cities") or []

    unlocked: List[Dict[str, Optional[str]]] = []
    for city in cities:
        city_name = city.get("cityName")
        for district in city.get("districts") or []:
            if district.get("isLocked") is False:
                unlocked.append(
                    {
                        "id": _normalize_identifier(district.get("id")),
                        "name": _normalize_text(district.get("name")),
                        "city": _normalize_text(city_name),
                    }
                )
    return unlocked


def apply_territory_validation(
    user_choice: Dict[str, object],
    unlocked_districts: List[Dict[str, Optional[str]]],
) -> Tuple[List[str], List[str], List[str]]:
    """
    Inject unlocked district identifiers into ``user_choice`` and find locked selections.

    Returns a tuple of (unlocked_names, unlocked_ids, locked_requests).
    """

    unlocked_names = [d["name"] for d in unlocked_districts if d.get("name")]
    unlocked_ids = [d["id"] for d in unlocked_districts if d.get("id")]

    if user_choice is not None:
        user_choice["districts_unlocked"] = unlocked_names
        user_choice["district_ids_unlocked"] = unlocked_ids

    available_name_set = set(unlocked_names)
    available_id_set = set(unlocked_ids)

    requested_ids, requested_names = _collect_requested_districts(user_choice)

    locked: Set[str] = set()
    for district_id in requested_ids:
        if district_id and district_id not in available_id_set:
            locked.add(district_id)
    for district_name in requested_names:
        if district_name and district_name not in available_name_set:
            locked.add(district_name)

    return unlocked_names, unlocked_ids, sorted(locked)


def _collect_requested_districts(
    user_choice: Optional[Dict[str, object]]
) -> Tuple[Set[str], Set[str]]:
    if not user_choice:
        return set(), set()

    id_keys = (
        "districtId",
        "district_id",
        "districtIds",
        "district_ids",
        "selectedDistrictIds",
        "nearbyDistrictIds",
    )
    name_keys = (
        "district",
        "districtName",
        "districts",
        "selectedDistricts",
        "nearbyDistricts",
    )

    requested_ids: Set[str] = set()
    requested_names: Set[str] = set()

    for key in id_keys:
        _collect_identifier(user_choice.get(key), requested_ids, treat_as_id=True)

    for key in name_keys:
        _collect_identifier(user_choice.get(key), requested_names, treat_as_id=False)

    return requested_ids, requested_names


def _collect_identifier(
    value: object,
    bucket: Set[str],
    *,
    treat_as_id: bool,
) -> None:
    if value is None:
        return

    if isinstance(value, str):
        normalized = _normalize_identifier(value)
        if normalized:
            bucket.add(normalized)
        return

    if isinstance(value, (int, float)):
        normalized_num = _normalize_identifier(value)
        if normalized_num:
            bucket.add(normalized_num)
        return

    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_identifier(item, bucket, treat_as_id=treat_as_id)
        return

    if isinstance(value, dict):
        if treat_as_id:
            for key in ("id", "districtId", "code"):
                if key in value:
                    _collect_identifier(value[key], bucket, treat_as_id=True)
        else:
            for key in ("name", "districtName", "label"):
                if key in value:
                    _collect_identifier(value[key], bucket, treat_as_id=False)
        return


def _normalize_identifier(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _normalize_text(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)
