from django.test import SimpleTestCase

from planner.domain.optimizer import FuelPlanningError, optimize_fuel_plan
from planner.domain.types import FuelNode


class FuelOptimizationTests(SimpleTestCase):
    def test_prefers_cheaper_station_ahead(self):
        nodes = [
            FuelNode(key="start", distance_miles=0.0, price_per_gallon=4.5, purchasable=True, station=None),
            FuelNode(key="s1", distance_miles=200.0, price_per_gallon=4.0, purchasable=True, station=None),
            FuelNode(key="s2", distance_miles=450.0, price_per_gallon=3.0, purchasable=True, station=None),
            FuelNode(key="s3", distance_miles=700.0, price_per_gallon=5.0, purchasable=True, station=None),
            FuelNode(key="end", distance_miles=900.0, price_per_gallon=None, purchasable=False, station=None),
        ]

        total_cost, total_gallons, actions = optimize_fuel_plan(
            nodes=nodes,
            mpg=10.0,
            max_range_miles=500.0,
        )

        purchased_nodes = [action.node.key for action in actions]
        self.assertEqual(purchased_nodes, ["start", "s1", "s2"])
        self.assertAlmostEqual(total_gallons, 90.0, places=3)
        self.assertAlmostEqual(total_cost, 325.0, places=2)

    def test_raises_when_segment_exceeds_range(self):
        nodes = [
            FuelNode(key="start", distance_miles=0.0, price_per_gallon=3.5, purchasable=True, station=None),
            FuelNode(key="end", distance_miles=700.0, price_per_gallon=None, purchasable=False, station=None),
        ]

        with self.assertRaises(FuelPlanningError):
            optimize_fuel_plan(nodes=nodes, mpg=10.0, max_range_miles=500.0)
