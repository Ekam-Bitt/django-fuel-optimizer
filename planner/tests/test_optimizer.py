from django.test import SimpleTestCase

from planner.domain.optimizer import FuelPlanningError, optimize_fuel_plan
from planner.domain.types import FuelNode, StationCandidate


def _station(station_id: int, price_per_gallon: float, along_distance_miles: float) -> StationCandidate:
    return StationCandidate(
        station_id=station_id,
        opis_truckstop_id=str(station_id),
        name=f"Station {station_id}",
        address="Address",
        city="City",
        state="TX",
        price_per_gallon=price_per_gallon,
        latitude=32.0,
        longitude=-96.0,
        along_distance_miles=along_distance_miles,
        distance_to_route_miles=1.0,
    )


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

    def test_stop_penalty_prefers_fewer_stops_when_savings_are_small(self):
        nodes = [
            FuelNode(key="start", distance_miles=0.0, price_per_gallon=3.5, purchasable=True, station=None),
            FuelNode(
                key="s1",
                distance_miles=250.0,
                price_per_gallon=3.4,
                purchasable=True,
                station=_station(1, 3.4, 250.0),
            ),
            FuelNode(
                key="s2",
                distance_miles=490.0,
                price_per_gallon=3.39,
                purchasable=True,
                station=_station(2, 3.39, 490.0),
            ),
            FuelNode(key="end", distance_miles=700.0, price_per_gallon=None, purchasable=False, station=None),
        ]

        _, _, baseline_actions = optimize_fuel_plan(
            nodes=nodes,
            mpg=10.0,
            max_range_miles=500.0,
            stop_penalty_usd=0.0,
        )
        _, _, penalized_actions = optimize_fuel_plan(
            nodes=nodes,
            mpg=10.0,
            max_range_miles=500.0,
            stop_penalty_usd=1.0,
        )

        self.assertEqual([action.node.key for action in baseline_actions], ["start", "s1", "s2"])
        self.assertEqual([action.node.key for action in penalized_actions], ["start", "s1"])

    def test_min_stop_gallons_prunes_micro_topup_when_feasible(self):
        nodes = [
            FuelNode(key="start", distance_miles=0.0, price_per_gallon=4.0, purchasable=True, station=None),
            FuelNode(
                key="s1",
                distance_miles=450.0,
                price_per_gallon=3.6,
                purchasable=True,
                station=_station(3, 3.6, 450.0),
            ),
            FuelNode(
                key="s2",
                distance_miles=890.0,
                price_per_gallon=3.3,
                purchasable=True,
                station=_station(4, 3.3, 890.0),
            ),
            FuelNode(
                key="s3",
                distance_miles=920.0,
                price_per_gallon=3.2,
                purchasable=True,
                station=_station(5, 3.2, 920.0),
            ),
            FuelNode(key="end", distance_miles=921.0, price_per_gallon=None, purchasable=False, station=None),
        ]

        _, _, actions = optimize_fuel_plan(
            nodes=nodes,
            mpg=10.0,
            max_range_miles=500.0,
            min_stop_gallons=1.0,
        )

        purchased_nodes = [action.node.key for action in actions]
        self.assertEqual(purchased_nodes, ["start", "s1", "s2"])
        self.assertTrue(all(action.gallons_purchased >= 1.0 for action in actions[1:]))
