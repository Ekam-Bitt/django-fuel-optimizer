import hashlib
from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.cache import cache

MILES_PER_METER = 0.000621371


@dataclass(frozen=True)
class RouteResult:
    distance_miles: float
    duration_minutes: float
    geometry: list[list[float]]
    provider: str


class RoutingError(Exception):
    pass


def _cache_key(provider: str, points: list[tuple[float, float]], profile: str = "") -> str:
    serialized = ";".join(f"{round(lat, 5)}:{round(lon, 5)}" for lat, lon in points)
    payload = f"{provider}:{profile}::{serialized}".encode("utf-8")
    return f"route::{hashlib.sha256(payload).hexdigest()}"


def _request_json(url: str, params: dict[str, str]) -> dict:
    response = requests.get(
        url,
        params=params,
        timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _dedupe_consecutive_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    deduped: list[tuple[float, float]] = []
    for point in points:
        if not deduped:
            deduped.append(point)
            continue
        prev = deduped[-1]
        if abs(prev[0] - point[0]) < 1e-7 and abs(prev[1] - point[1]) < 1e-7:
            continue
        deduped.append(point)
    return deduped


def _fetch_mapbox_route(points: list[tuple[float, float]]) -> RouteResult:
    token = settings.MAPBOX_ACCESS_TOKEN
    if not token:
        raise RoutingError("MAPBOX_ACCESS_TOKEN is required when MAP_PROVIDER=mapbox")

    if len(points) > 25:
        raise RoutingError("Mapbox supports up to 25 coordinates per route request")

    profile = settings.MAPBOX_DIRECTIONS_PROFILE
    coordinate_string = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"https://api.mapbox.com/directions/v5/mapbox/{profile}/{coordinate_string}"

    payload = _request_json(
        url,
        params={
            "alternatives": "false",
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
            "access_token": token,
        },
    )

    if payload.get("code") != "Ok" or not payload.get("routes"):
        message = payload.get("message", "route not available")
        raise RoutingError(f"Mapbox directions failed: {message}")

    route = payload["routes"][0]
    return RouteResult(
        distance_miles=float(route["distance"]) * MILES_PER_METER,
        duration_minutes=float(route["duration"]) / 60.0,
        geometry=route["geometry"]["coordinates"],
        provider="mapbox",
    )


def _fetch_osrm_route(points: list[tuple[float, float]]) -> RouteResult:
    coordinate_string = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"{settings.OSRM_API_BASE_URL}/route/v1/driving/{coordinate_string}"

    payload = _request_json(
        url,
        params={
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        },
    )

    if payload.get("code") != "Ok" or not payload.get("routes"):
        message = payload.get("message", "route not available")
        raise RoutingError(f"OSRM directions failed: {message}")

    route = payload["routes"][0]
    return RouteResult(
        distance_miles=float(route["distance"]) * MILES_PER_METER,
        duration_minutes=float(route["duration"]) / 60.0,
        geometry=route["geometry"]["coordinates"],
        provider="osrm",
    )


def _resolve_provider() -> str:
    value = settings.MAP_PROVIDER
    if value in {"mapbox", "osrm", "auto"}:
        return value
    return "auto"


def fetch_route_through_points(points: list[tuple[float, float]]) -> RouteResult:
    normalized_points = _dedupe_consecutive_points(points)
    if len(normalized_points) < 2:
        raise RoutingError("At least two coordinates are required to build a route")

    provider = _resolve_provider()
    candidate_providers = ["mapbox", "osrm"] if provider == "auto" else [provider]

    errors: list[str] = []
    for candidate in candidate_providers:
        profile = settings.MAPBOX_DIRECTIONS_PROFILE if candidate == "mapbox" else ""
        key = _cache_key(candidate, normalized_points, profile)
        cached = cache.get(key)
        if cached:
            return cached

        try:
            if candidate == "mapbox":
                result = _fetch_mapbox_route(normalized_points)
            else:
                result = _fetch_osrm_route(normalized_points)
        except RoutingError as exc:
            errors.append(f"{candidate}: {exc}")
            if provider != "auto":
                raise
            continue

        cache.set(key, result, timeout=24 * 60 * 60)
        return result

    detail = "; ".join(errors) if errors else "No routing providers available"
    raise RoutingError(f"Unable to build route: {detail}")


def fetch_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> RouteResult:
    return fetch_route_through_points(
        points=[(start_lat, start_lon), (end_lat, end_lon)],
    )
