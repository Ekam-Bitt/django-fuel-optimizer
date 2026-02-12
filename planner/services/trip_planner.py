from typing import Any

from django.conf import settings

from planner.domain.optimizer import optimize_fuel_plan
from planner.domain.types import FuelNode, StopAction
from planner.services.distance import cumulative_route_distances
from planner.services.geocoding import geocode_location
from planner.services.routing import fetch_route, fetch_route_through_points
from planner.services.station_locator import (
    estimate_start_price,
    fetch_route_station_candidates,
)


def _extract_city_state(location_query: str) -> tuple[str, str]:
    parts = [part.strip() for part in location_query.split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return parts[0], "-"
    return "-", "-"


def _serialize_stop_action(
    action: StopAction,
    sequence: int,
    origin_latitude: float,
    origin_longitude: float,
    origin_city: str,
    origin_state: str,
) -> dict[str, Any]:
    node = action.node

    if node.station is None:
        return {
            "sequence": sequence,
            "kind": "origin_estimate",
            "name": "Origin Fuel Estimate",
            "city": origin_city,
            "state": origin_state,
            "price_per_gallon": round(float(node.price_per_gallon), 4),
            "gallons_purchased": round(action.gallons_purchased, 3),
            "estimated_cost": round(action.purchase_cost, 2),
            "distance_from_start_miles": 0.0,
            "location": {
                "latitude": origin_latitude,
                "longitude": origin_longitude,
            },
        }

    station = node.station
    return {
        "sequence": sequence,
        "kind": "fuel_station",
        "station_id": station.station_id,
        "opis_truckstop_id": station.opis_truckstop_id,
        "name": station.name,
        "address": station.address,
        "city": station.city,
        "state": station.state,
        "price_per_gallon": round(station.price_per_gallon, 4),
        "distance_to_route_miles": round(station.distance_to_route_miles, 3),
        "distance_from_start_miles": round(station.along_distance_miles, 3),
        "gallons_purchased": round(action.gallons_purchased, 3),
        "estimated_cost": round(action.purchase_cost, 2),
        "location": {
            "latitude": station.latitude,
            "longitude": station.longitude,
        },
    }


def build_trip_plan(
    start_location: str,
    end_location: str,
    mpg: float = 10.0,
    max_range_miles: float = 500.0,
    route_mode: str = "direct",
    max_stop_detour_miles: float | None = None,
    min_stop_gallons: float | None = None,
    stop_penalty_usd: float | None = None,
) -> dict[str, Any]:
    if min_stop_gallons is None:
        min_stop_gallons = float(settings.DEFAULT_MIN_STOP_GALLONS)
    if stop_penalty_usd is None:
        stop_penalty_usd = float(settings.DEFAULT_STOP_PENALTY_USD)
    if max_stop_detour_miles is None:
        max_stop_detour_miles = settings.DEFAULT_MAX_STOP_DETOUR_MILES

    origin = geocode_location(start_location)
    destination = geocode_location(end_location)
    origin_city, origin_state = _extract_city_state(start_location)

    route = fetch_route(
        start_lat=origin.latitude,
        start_lon=origin.longitude,
        end_lat=destination.latitude,
        end_lon=destination.longitude,
    )

    corridor_miles = float(settings.ROUTE_CORRIDOR_MILES)
    route_cumulative_miles = cumulative_route_distances(route.geometry)
    candidates = fetch_route_station_candidates(
        route_geometry=route.geometry,
        route_cumulative_miles=route_cumulative_miles,
        corridor_miles=corridor_miles,
    )
    candidate_count_before_detour_filter = len(candidates)
    if max_stop_detour_miles is None:
        effective_max_detour = corridor_miles
    else:
        effective_max_detour = min(max_stop_detour_miles, corridor_miles)
    candidates = [
        candidate for candidate in candidates if candidate.distance_to_route_miles <= effective_max_detour + 1e-6
    ]

    route_total_miles = route.distance_miles
    nodes: list[FuelNode] = [
        FuelNode(
            key="start",
            distance_miles=0.0,
            price_per_gallon=estimate_start_price(candidates),
            purchasable=True,
            station=None,
        )
    ]

    for candidate in candidates:
        if 0.1 < candidate.along_distance_miles < route_total_miles - 0.1:
            nodes.append(
                FuelNode(
                    key=f"station-{candidate.station_id}",
                    distance_miles=candidate.along_distance_miles,
                    price_per_gallon=candidate.price_per_gallon,
                    purchasable=True,
                    station=candidate,
                )
            )

    nodes.append(
        FuelNode(
            key="end",
            distance_miles=route_total_miles,
            price_per_gallon=None,
            purchasable=False,
            station=None,
        )
    )
    nodes = sorted(nodes, key=lambda item: item.distance_miles)

    total_cost, total_gallons, actions = optimize_fuel_plan(
        nodes=nodes,
        mpg=mpg,
        max_range_miles=max_range_miles,
        min_stop_gallons=min_stop_gallons,
        stop_penalty_usd=stop_penalty_usd,
    )

    rendered_route = route
    route_api_calls = 1
    if route_mode == "via_stops":
        waypoint_points: list[tuple[float, float]] = [(origin.latitude, origin.longitude)]
        for action in actions:
            station = action.node.station
            if station is None:
                continue
            waypoint_points.append((station.latitude, station.longitude))
        waypoint_points.append((destination.latitude, destination.longitude))

        if len(waypoint_points) > 2:
            rendered_route = fetch_route_through_points(waypoint_points)
            route_api_calls = 2

    return {
        "origin": {
            "query": start_location,
            "resolved": origin.display_name,
            "latitude": origin.latitude,
            "longitude": origin.longitude,
            "source": origin.source,
        },
        "destination": {
            "query": end_location,
            "resolved": destination.display_name,
            "latitude": destination.latitude,
            "longitude": destination.longitude,
            "source": destination.source,
        },
        "route": {
            "distance_miles": round(rendered_route.distance_miles, 3),
            "duration_minutes": round(rendered_route.duration_minutes, 2),
            "geometry": {
                "type": "LineString",
                "coordinates": rendered_route.geometry,
            },
        },
        "fuel_plan": {
            "max_range_miles": max_range_miles,
            "mpg": mpg,
            "estimated_total_gallons_purchased": round(total_gallons, 3),
            "estimated_total_cost_usd": round(total_cost, 2),
            "stops": [
                _serialize_stop_action(
                    action=action,
                    sequence=index,
                    origin_latitude=origin.latitude,
                    origin_longitude=origin.longitude,
                    origin_city=origin_city,
                    origin_state=origin_state,
                )
                for index, action in enumerate(actions, start=1)
            ],
        },
        "meta": {
            "route_api_calls": route_api_calls,
            "route_provider": rendered_route.provider,
            "route_mode": route_mode,
            "candidate_stations_considered": candidate_count_before_detour_filter,
            "candidate_stations_after_detour_filter": len(candidates),
            "route_station_corridor_miles": corridor_miles,
            "max_stop_detour_miles": effective_max_detour,
            "min_stop_gallons": min_stop_gallons,
            "stop_penalty_usd": stop_penalty_usd,
            "assumptions": [
                "Trip starts with an empty tank and purchases fuel at the best next stop strategy.",
                "Fuel station coordinates are approximated from city/state postal geography.",
                "Direct mode fetches one origin-to-destination route and optimizes stops near it.",
                "Via_stops mode fetches an additional waypoint route for map geometry through selected stops.",
                "Optimizer can prune low-value stops using minimum gallons and per-stop penalty settings.",
            ],
        },
    }
