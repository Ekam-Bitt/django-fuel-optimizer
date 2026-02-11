import math

EARTH_RADIUS_MILES = 3958.8


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = lat2_rad - lat1_rad
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_MILES * c


def cumulative_route_distances(route_coordinates: list[list[float]]) -> list[float]:
    if not route_coordinates:
        return []

    cumulative = [0.0]
    total = 0.0
    for idx in range(1, len(route_coordinates)):
        prev_lon, prev_lat = route_coordinates[idx - 1]
        lon, lat = route_coordinates[idx]
        total += haversine_miles(prev_lat, prev_lon, lat, lon)
        cumulative.append(total)
    return cumulative
