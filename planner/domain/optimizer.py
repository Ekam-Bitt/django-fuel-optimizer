from planner.domain.types import FuelNode, StopAction


class FuelPlanningError(Exception):
    pass


def optimize_fuel_plan(
    nodes: list[FuelNode],
    mpg: float,
    max_range_miles: float,
) -> tuple[float, float, list[StopAction]]:
    if mpg <= 0:
        raise FuelPlanningError("Miles per gallon must be greater than zero")
    if max_range_miles <= 0:
        raise FuelPlanningError("Max range must be greater than zero")
    if len(nodes) < 2:
        raise FuelPlanningError("At least start and end nodes are required")

    tank_capacity_gallons = max_range_miles / mpg
    current_fuel_gallons = 0.0
    total_cost = 0.0
    total_gallons = 0.0
    stop_actions: list[StopAction] = []

    for idx in range(len(nodes) - 1):
        current_node = nodes[idx]
        next_node = nodes[idx + 1]
        segment_distance_miles = next_node.distance_miles - current_node.distance_miles

        if segment_distance_miles < -1e-6:
            raise FuelPlanningError("Fuel nodes are not ordered by distance")
        if segment_distance_miles > max_range_miles + 1e-6:
            raise FuelPlanningError("Route cannot be completed: a segment exceeds vehicle max range")

        reachable_indexes: list[int] = []
        probe = idx + 1
        while probe < len(nodes):
            probe_distance = nodes[probe].distance_miles - current_node.distance_miles
            if probe_distance > max_range_miles + 1e-6:
                break
            reachable_indexes.append(probe)
            probe += 1

        if not reachable_indexes:
            raise FuelPlanningError("No reachable node within max range")

        cheaper_station_index = None
        if current_node.price_per_gallon is not None:
            for reachable_idx in reachable_indexes:
                candidate_price = nodes[reachable_idx].price_per_gallon
                if candidate_price is not None and candidate_price < current_node.price_per_gallon:
                    cheaper_station_index = reachable_idx
                    break

        if cheaper_station_index is not None:
            target_distance = nodes[cheaper_station_index].distance_miles - current_node.distance_miles
            target_fuel = target_distance / mpg
        else:
            distance_to_end = nodes[-1].distance_miles - current_node.distance_miles
            target_fuel = distance_to_end / mpg if distance_to_end <= max_range_miles + 1e-6 else tank_capacity_gallons

        gallons_to_buy = max(0.0, target_fuel - current_fuel_gallons)

        if gallons_to_buy > 1e-6:
            if not current_node.purchasable or current_node.price_per_gallon is None:
                raise FuelPlanningError("Required fuel purchase at a non-purchasable node")

            purchase_cost = gallons_to_buy * current_node.price_per_gallon
            current_fuel_gallons += gallons_to_buy
            total_gallons += gallons_to_buy
            total_cost += purchase_cost
            stop_actions.append(
                StopAction(
                    node=current_node,
                    gallons_purchased=gallons_to_buy,
                    purchase_cost=purchase_cost,
                )
            )

        fuel_needed = segment_distance_miles / mpg
        current_fuel_gallons -= fuel_needed
        if current_fuel_gallons < -1e-6:
            raise FuelPlanningError("Calculated negative fuel balance")
        current_fuel_gallons = max(current_fuel_gallons, 0.0)

    return total_cost, total_gallons, stop_actions
