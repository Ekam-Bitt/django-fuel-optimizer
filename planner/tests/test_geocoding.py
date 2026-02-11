from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase

from planner.services.geocoding import GeocodedPoint, geocode_location


class GeocodingServiceTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch("planner.services.geocoding._remote_lookup")
    @patch("planner.services.geocoding._local_lookup")
    def test_prefers_local_lookup_before_remote(self, mock_local_lookup, mock_remote_lookup):
        mock_local_lookup.return_value = GeocodedPoint(
            latitude=32.0,
            longitude=-96.0,
            display_name="Dallas, TX",
            source="pgeocode-local",
        )

        result = geocode_location("Dallas, TX")

        self.assertEqual(result.source, "pgeocode-local")
        mock_remote_lookup.assert_not_called()

    @patch("planner.services.geocoding._remote_lookup")
    @patch("planner.services.geocoding._local_lookup")
    def test_uses_remote_lookup_when_local_misses(self, mock_local_lookup, mock_remote_lookup):
        mock_local_lookup.return_value = None
        mock_remote_lookup.return_value = GeocodedPoint(
            latitude=30.0,
            longitude=-97.0,
            display_name="Austin, TX",
            source="nominatim",
        )

        result = geocode_location("Austin, TX")

        self.assertEqual(result.source, "nominatim")
        mock_remote_lookup.assert_called_once()
