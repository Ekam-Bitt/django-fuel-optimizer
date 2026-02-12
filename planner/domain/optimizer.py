from planner.domain.types import FuelNode, StopAction

EPSILON = 1e-6
SMALL_STOP_PENALTY_USD = 1_000_000.0


class FuelPlanningError(Exception):
    pass


def _station_stop_count(actions: list[StopAction]) -> int:
    return sum(1 for action in actions if action.node.station is not None)


def _small_stop_count(actions: list[StopAction], min_stop_gallons: float) -> int:
    if min_stop_gallons <= 0:
        return 0
    return sum(
        1
        for action in actions
        if action.node.station is not None and action.gallons_purchased + EPSILON < min_stop_gallons
    )


def _plan_objective(
    total_cost: float,
    actions: list[StopAction],
    stop_penalty_usd: float,
    min_stop_gallons: float,
) -> float:
    return (
        total_cost
        + (_station_stop_count(actions) * stop_penalty_usd)
        + (_small_stop_count(actions, min_stop_gallons) * SMALL_STOP_PENALTY_USD)
    )


def _remove_node(nodes: list[FuelNode], node_key: str) -> list[FuelNode]:
    return [node for node in nodes if node.key != node_key]


def _remove_nodes(nodes: list[FuelNode], node_keys: set[str]) -> list[FuelNode]:
    return [node for node in nodes if node.key not in node_keys]


def _near_end_small_stop_keys(nodes: list[FuelNode], min_stop_gallons: float, mpg: float) -> set[str]:
    if min_stop_gallons <= 0 or mpg <= 0:
        return set()

    end_distance = nodes[-1].distance_miles
    keys: set[str] = set()
    for node in nodes:
        if node.station is None:
            continue
        gallons_to_destination = (end_distance - node.distance_miles) / mpg
        if gallons_to_destination + EPSILON < min_stop_gallons:
            keys.add(node.key)
    return keys


def _run_greedy_plan(
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

        if segment_distance_miles < -EPSILON:
            raise FuelPlanningError("Fuel nodes are not ordered by distance")
        if segment_distance_miles > max_range_miles + EPSILON:
            raise FuelPlanningError("Route cannot be completed: a segment exceeds vehicle max range")

        reachable_indexes: list[int] = []
        probe = idx + 1
        while probe < len(nodes):
            probe_distance = nodes[probe].distance_miles - current_node.distance_miles
            if probe_distance > max_range_miles + EPSILON:
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
            if distance_to_end <= max_range_miles + EPSILON:
                target_fuel = distance_to_end / mpg
            else:
                target_fuel = tank_capacity_gallons

        gallons_to_buy = max(0.0, target_fuel - current_fuel_gallons)

        if gallons_to_buy > EPSILON:
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
        if current_fuel_gallons < -EPSILON:
            raise FuelPlanningError("Calculated negative fuel balance")
        current_fuel_gallons = max(current_fuel_gallons, 0.0)

    return total_cost, total_gallons, stop_actions


def optimize_fuel_plan(
    nodes: list[FuelNode],
    mpg: float,
    max_range_miles: float,
    min_stop_gallons: float = 0.0,
    stop_penalty_usd: float = 0.0,
) -> tuple[float, float, list[StopAction]]:
    if min_stop_gallons < 0:
        raise FuelPlanningError("Minimum stop gallons cannot be negative")
    if stop_penalty_usd < 0:
        raise FuelPlanningError("Stop penalty cannot be negative")

    optimized_nodes = list(nodes)
    total_cost, total_gallons, stop_actions = _run_greedy_plan(
        nodes=optimized_nodes,
        mpg=mpg,
        max_range_miles=max_range_miles,
    )

    if stop_penalty_usd <= 0 and min_stop_gallons <= 0:
        return total_cost, total_gallons, stop_actions

    while True:
        current_objective = _plan_objective(
            total_cost=total_cost,
            actions=stop_actions,
            stop_penalty_usd=stop_penalty_usd,
            min_stop_gallons=min_stop_gallons,
        )

        best_candidate: tuple[list[FuelNode], float, float, list[StopAction], float] | None = None
        candidate_node_sets: list[set[str]] = []
        for action in stop_actions:
            if action.node.station is None:
                continue
            candidate_node_sets.append({action.node.key})

        near_end_small_keys = _near_end_small_stop_keys(
            nodes=optimized_nodes,
            min_stop_gallons=min_stop_gallons,
            mpg=mpg,
        )
        if near_end_small_keys:
            candidate_node_sets.append(near_end_small_keys)

        for candidate_keys in candidate_node_sets:
            if len(candidate_keys) == 1:
                candidate_nodes = _remove_node(optimized_nodes, next(iter(candidate_keys)))
            else:
                candidate_nodes = _remove_nodes(optimized_nodes, candidate_keys)

            try:
                candidate_cost, candidate_gallons, candidate_actions = _run_greedy_plan(
                    nodes=candidate_nodes,
                    mpg=mpg,
                    max_range_miles=max_range_miles,
                )
            except FuelPlanningError:
                continue

            candidate_objective = _plan_objective(
                total_cost=candidate_cost,
                actions=candidate_actions,
                stop_penalty_usd=stop_penalty_usd,
                min_stop_gallons=min_stop_gallons,
            )
            if candidate_objective + EPSILON >= current_objective:
                continue

            if best_candidate is None or candidate_objective < best_candidate[4]:
                best_candidate = (
                    candidate_nodes,
                    candidate_cost,
                    candidate_gallons,
                    candidate_actions,
                    candidate_objective,
                )

        if best_candidate is None:
            break

        optimized_nodes = best_candidate[0]
        total_cost = best_candidate[1]
        total_gallons = best_candidate[2]
        stop_actions = best_candidate[3]

    return total_cost, total_gallons, stop_actions
