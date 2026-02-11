import math

from django.db.models import Avg

from planner.domain.types import StationCandidate
from planner.models import FuelStation
from planner.services.distance import haversine_miles

MAX_ROUTE_SAMPLE_POINTS = 350
STATION_BUCKET_MILES = 35.0
MAX_STATIONS_PER_BUCKET = 3
START_PRICE_WINDOW_MILES = 40.0
DEFAULT_START_PRICE = 3.5


def _bbox_from_route(
    route_geometry: list[list[float]],
    corridor_miles: float,
) -> tuple[float, float, float, float]:
    lats = [coord[1] for coord in route_geometry]
    lons = [coord[0] for coord in route_geometry]

    min_lat = min(lats)
    max_lat = max(lats)
    min_lon = min(lons)
    max_lon = max(lons)

    mid_lat = (min_lat + max_lat) / 2.0
    lat_pad = corridor_miles / 69.0
    lon_pad = corridor_miles / max(69.0 * abs(math.cos(math.radians(mid_lat))), 15.0)

    return (
        min_lat - lat_pad,
        max_lat + lat_pad,
        min_lon - lon_pad,
        max_lon + lon_pad,
    )


def _build_sample_indexes(
    route_geometry: list[list[float]],
    max_samples: int = MAX_ROUTE_SAMPLE_POINTS,
) -> list[int]:
    if not route_geometry:
        return []
    if len(route_geometry) <= max_samples:
        return list(range(len(route_geometry)))

    step = max(1, len(route_geometry) // max_samples)
    indexes = list(range(0, len(route_geometry), step))
    if indexes[-1] != len(route_geometry) - 1:
        indexes.append(len(route_geometry) - 1)
    return indexes


def _project_station_to_route(
    station_lat: float,
    station_lon: float,
    route_geometry: list[list[float]],
    sample_indexes: list[int],
    route_cumulative_miles: list[float],
) -> tuple[float, float]:
    best_distance = float("inf")
    best_along_distance = 0.0

    for idx in sample_indexes:
        lon, lat = route_geometry[idx]
        distance = haversine_miles(station_lat, station_lon, lat, lon)
        if distance < best_distance:
            best_distance = distance
            best_along_distance = route_cumulative_miles[idx]

    return best_distance, best_along_distance


def _prune_candidates(candidates: list[StationCandidate]) -> list[StationCandidate]:
    bucketed: dict[int, list[StationCandidate]] = {}
    for candidate in candidates:
        bucket = int(candidate.along_distance_miles // STATION_BUCKET_MILES)
        bucketed.setdefault(bucket, []).append(candidate)

    selected: list[StationCandidate] = []
    for bucket in sorted(bucketed):
        bucket_candidates = sorted(
            bucketed[bucket],
            key=lambda item: (item.price_per_gallon, item.distance_to_route_miles),
        )
        selected.extend(bucket_candidates[:MAX_STATIONS_PER_BUCKET])

    return sorted(selected, key=lambda item: item.along_distance_miles)


def fetch_route_station_candidates(
    route_geometry: list[list[float]],
    route_cumulative_miles: list[float],
    corridor_miles: float,
) -> list[StationCandidate]:
    min_lat, max_lat, min_lon, max_lon = _bbox_from_route(route_geometry, corridor_miles)

    rows = FuelStation.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lon,
        longitude__lte=max_lon,
    ).values(
        "id",
        "opis_truckstop_id",
        "truckstop_name",
        "address",
        "city",
        "state",
        "retail_price",
        "latitude",
        "longitude",
    )

    sample_indexes = _build_sample_indexes(route_geometry)
    candidates: list[StationCandidate] = []

    for row in rows.iterator():
        distance_to_route, along_distance = _project_station_to_route(
            station_lat=float(row["latitude"]),
            station_lon=float(row["longitude"]),
            route_geometry=route_geometry,
            sample_indexes=sample_indexes,
            route_cumulative_miles=route_cumulative_miles,
        )
        if distance_to_route > corridor_miles:
            continue

        candidates.append(
            StationCandidate(
                station_id=int(row["id"]),
                opis_truckstop_id=str(row["opis_truckstop_id"]),
                name=str(row["truckstop_name"]),
                address=str(row["address"]),
                city=str(row["city"]),
                state=str(row["state"]),
                price_per_gallon=float(row["retail_price"]),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                along_distance_miles=along_distance,
                distance_to_route_miles=distance_to_route,
            )
        )

    return _prune_candidates(candidates)


def estimate_start_price(candidates: list[StationCandidate]) -> float:
    near_start = [candidate for candidate in candidates if candidate.along_distance_miles <= START_PRICE_WINDOW_MILES]
    if near_start:
        return min(candidate.price_per_gallon for candidate in near_start)

    average_price = FuelStation.objects.aggregate(avg_price=Avg("retail_price"))["avg_price"]
    return float(average_price) if average_price is not None else DEFAULT_START_PRICE
