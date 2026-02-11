import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache

import requests
from django.conf import settings
from django.core.cache import cache

from planner.services.city_locator import CityLocator

CITY_STATE_RE = re.compile(r"^\s*(?P<city>[^,]+?)\s*,\s*(?P<state>[A-Za-z]{2})\s*$")


@dataclass(frozen=True)
class GeocodedPoint:
    latitude: float
    longitude: float
    display_name: str
    source: str


class GeocodingError(Exception):
    pass


@lru_cache(maxsize=1)
def _get_city_locator() -> CityLocator:
    return CityLocator()


def _cache_key(query: str) -> str:
    digest = hashlib.sha256(query.lower().strip().encode("utf-8")).hexdigest()
    return f"geocode::{digest}"


def _parse_city_state(query: str) -> tuple[str, str] | None:
    match = CITY_STATE_RE.match(query)
    if not match:
        return None
    return match.group("city").strip(), match.group("state").upper()


def _local_lookup(query: str) -> GeocodedPoint | None:
    parsed = _parse_city_state(query)
    if parsed is None:
        return None

    city, state = parsed
    local_match = _get_city_locator().lookup(city=city, state=state)
    if local_match is None:
        return None

    return GeocodedPoint(
        latitude=local_match.latitude,
        longitude=local_match.longitude,
        display_name=f"{city}, {state}",
        source="pgeocode-local",
    )


def _remote_lookup(query: str) -> GeocodedPoint | None:
    response = requests.get(
        f"{settings.NOMINATIM_API_BASE_URL}/search",
        params={
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 1,
            "countrycodes": "us",
        },
        headers={"User-Agent": settings.GEOLOOKUP_USER_AGENT},
        timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    if not payload:
        return None

    item = payload[0]
    return GeocodedPoint(
        latitude=float(item["lat"]),
        longitude=float(item["lon"]),
        display_name=item.get("display_name", query),
        source="nominatim",
    )


def geocode_location(query: str) -> GeocodedPoint:
    normalized_query = query.strip()
    if not normalized_query:
        raise GeocodingError("Location input cannot be empty")

    cache_key = _cache_key(normalized_query)
    cached = cache.get(cache_key)
    if cached:
        return cached

    local = _local_lookup(normalized_query)
    if local:
        cache.set(cache_key, local, timeout=24 * 60 * 60)
        return local

    remote = _remote_lookup(normalized_query)
    if remote:
        cache.set(cache_key, remote, timeout=24 * 60 * 60)
        return remote

    raise GeocodingError(f"Unable to geocode location: {normalized_query}")
