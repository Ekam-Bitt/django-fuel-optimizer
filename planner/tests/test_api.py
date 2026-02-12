from unittest.mock import patch

from django.conf import settings
from django.test import TestCase


class TripPlanApiTests(TestCase):
    @patch("planner.api.views.build_trip_plan")
    def test_trip_plan_endpoint_returns_service_payload(self, mock_build_trip_plan):
        mock_build_trip_plan.return_value = {
            "origin": {"query": "A", "resolved": "A", "latitude": 0, "longitude": 0, "source": "test"},
            "destination": {"query": "B", "resolved": "B", "latitude": 1, "longitude": 1, "source": "test"},
            "route": {
                "distance_miles": 100,
                "duration_minutes": 120,
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            },
            "fuel_plan": {
                "max_range_miles": 500,
                "mpg": 10,
                "estimated_total_gallons_purchased": 10,
                "estimated_total_cost_usd": 35,
                "stops": [],
            },
            "meta": {
                "route_api_calls": 1,
                "route_provider": "test",
                "candidate_stations_considered": 0,
                "route_station_corridor_miles": 60,
                "assumptions": [],
            },
        }

        response = self.client.post(
            "/api/trip-plan/",
            data={
                "start_location": "Dallas, TX",
                "finish_location": "Austin, TX",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["route_api_calls"], 1)
        mock_build_trip_plan.assert_called_once_with(
            start_location="Dallas, TX",
            end_location="Austin, TX",
            mpg=10.0,
            max_range_miles=500.0,
            route_mode="direct",
            max_stop_detour_miles=settings.DEFAULT_MAX_STOP_DETOUR_MILES,
            min_stop_gallons=settings.DEFAULT_MIN_STOP_GALLONS,
            stop_penalty_usd=settings.DEFAULT_STOP_PENALTY_USD,
        )

    @patch("planner.api.views.build_trip_plan")
    def test_trip_plan_endpoint_accepts_route_mode(self, mock_build_trip_plan):
        mock_build_trip_plan.return_value = {
            "origin": {"query": "A", "resolved": "A", "latitude": 0, "longitude": 0, "source": "test"},
            "destination": {"query": "B", "resolved": "B", "latitude": 1, "longitude": 1, "source": "test"},
            "route": {
                "distance_miles": 100,
                "duration_minutes": 120,
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            },
            "fuel_plan": {
                "max_range_miles": 500,
                "mpg": 10,
                "estimated_total_gallons_purchased": 10,
                "estimated_total_cost_usd": 35,
                "stops": [],
            },
            "meta": {
                "route_api_calls": 2,
                "route_provider": "test",
                "route_mode": "via_stops",
                "candidate_stations_considered": 0,
                "route_station_corridor_miles": 60,
                "assumptions": [],
            },
        }
        response = self.client.post(
            "/api/trip-plan/",
            data={
                "start_location": "Chicago, IL",
                "finish_location": "Dallas, TX",
                "route_mode": "via_stops",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_build_trip_plan.assert_called_once_with(
            start_location="Chicago, IL",
            end_location="Dallas, TX",
            mpg=10.0,
            max_range_miles=500.0,
            route_mode="via_stops",
            max_stop_detour_miles=settings.DEFAULT_MAX_STOP_DETOUR_MILES,
            min_stop_gallons=settings.DEFAULT_MIN_STOP_GALLONS,
            stop_penalty_usd=settings.DEFAULT_STOP_PENALTY_USD,
        )

    @patch("planner.api.views.build_trip_plan")
    def test_trip_plan_endpoint_accepts_optimization_tuning(self, mock_build_trip_plan):
        mock_build_trip_plan.return_value = {
            "origin": {"query": "A", "resolved": "A", "latitude": 0, "longitude": 0, "source": "test"},
            "destination": {"query": "B", "resolved": "B", "latitude": 1, "longitude": 1, "source": "test"},
            "route": {
                "distance_miles": 100,
                "duration_minutes": 120,
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            },
            "fuel_plan": {
                "max_range_miles": 500,
                "mpg": 10,
                "estimated_total_gallons_purchased": 10,
                "estimated_total_cost_usd": 35,
                "stops": [],
            },
            "meta": {
                "route_api_calls": 1,
                "route_provider": "test",
                "candidate_stations_considered": 0,
                "route_station_corridor_miles": 60,
                "assumptions": [],
            },
        }
        response = self.client.post(
            "/api/trip-plan/",
            data={
                "start_location": "Chicago, IL",
                "finish_location": "Dallas, TX",
                "max_stop_detour_miles": 12,
                "min_stop_gallons": 2,
                "stop_penalty_usd": 3.25,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_build_trip_plan.assert_called_once_with(
            start_location="Chicago, IL",
            end_location="Dallas, TX",
            mpg=10.0,
            max_range_miles=500.0,
            route_mode="direct",
            max_stop_detour_miles=12.0,
            min_stop_gallons=2.0,
            stop_penalty_usd=3.25,
        )

    def test_trip_plan_endpoint_validates_payload(self):
        response = self.client.post(
            "/api/trip-plan/",
            data={"start_location": "Only one field"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("finish_location", response.json())

    def test_trip_plan_endpoint_enforces_assignment_mpg(self):
        response = self.client.post(
            "/api/trip-plan/",
            data={
                "start_location": "New York, NY",
                "finish_location": "Atlanta, GA",
                "mpg": 8,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("mpg", response.json())

    def test_trip_plan_endpoint_enforces_assignment_max_range(self):
        response = self.client.post(
            "/api/trip-plan/",
            data={
                "start_location": "New York, NY",
                "finish_location": "Atlanta, GA",
                "max_range_miles": 450,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("max_range_miles", response.json())
