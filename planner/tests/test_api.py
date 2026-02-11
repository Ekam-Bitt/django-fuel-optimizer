from unittest.mock import patch

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
        mock_build_trip_plan.assert_called_once()

    def test_trip_plan_endpoint_validates_payload(self):
        response = self.client.post(
            "/api/trip-plan/",
            data={"start_location": "Only one field"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("finish_location", response.json())
