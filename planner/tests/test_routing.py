from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from planner.services.routing import fetch_route


class RoutingServiceTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(MAP_PROVIDER="auto", MAPBOX_ACCESS_TOKEN="", OSRM_API_BASE_URL="https://osrm.test")
    @patch("planner.services.routing.requests.get")
    def test_auto_provider_falls_back_to_osrm_when_mapbox_key_missing(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "code": "Ok",
            "routes": [
                {
                    "distance": 1000,
                    "duration": 600,
                    "geometry": {"coordinates": [[-97.0, 32.7], [-97.1, 32.8]]},
                }
            ],
        }
        mock_get.return_value = response

        result = fetch_route(32.7763, -96.7969, 30.2672, -97.7431)

        self.assertEqual(result.provider, "osrm")
        mock_get.assert_called_once()

    @override_settings(MAP_PROVIDER="mapbox", MAPBOX_ACCESS_TOKEN="token-123", MAPBOX_DIRECTIONS_PROFILE="driving")
    @patch("planner.services.routing.requests.get")
    def test_mapbox_provider_uses_mapbox_endpoint(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "code": "Ok",
            "routes": [
                {
                    "distance": 2000,
                    "duration": 900,
                    "geometry": {"coordinates": [[-97.0, 32.7], [-97.1, 32.8]]},
                }
            ],
        }
        mock_get.return_value = response

        result = fetch_route(32.7763, -96.7969, 30.2672, -97.7431)

        self.assertEqual(result.provider, "mapbox")
        called_url = mock_get.call_args.kwargs.get("url", "") if mock_get.call_args else ""
        # requests.get is called with positional URL
        if not called_url:
            called_url = mock_get.call_args.args[0]
        self.assertIn("api.mapbox.com/directions", called_url)
