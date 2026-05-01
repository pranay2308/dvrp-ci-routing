from copy import deepcopy
from typing import Callable, Optional

from dvrp.models import Customer, Solution
from dvrp.cost import route_distance, is_capacity_feasible


def insert_customer_best_position(
    depot: Customer,
    solution: Solution,
    new_customer: Customer,
    dist_fn: Optional[Callable] = None,
) -> Optional[Solution]:
    """
    Insert a new customer into the best feasible position
    across all routes (minimum additional distance).

    Returns:
        New improved solution OR None if infeasible.
    """
    best_solution = None
    best_delta = float("inf")

    for route_idx, route in enumerate(solution.routes):
        # Capacity feasibility quick check
        if not is_capacity_feasible(
            route.customers + [new_customer],
            route.vehicle.capacity,
        ):
            continue

        original_cost = route_distance(depot, route.customers, dist_fn)

        # Try all insertion positions
        for pos in range(len(route.customers) + 1):
            candidate_customers = (
                route.customers[:pos]
                + [new_customer]
                + route.customers[pos:]
            )

            new_cost = route_distance(depot, candidate_customers, dist_fn)
            delta = new_cost - original_cost

            if delta < best_delta:
                best_delta = delta
                best_solution = deepcopy(solution)
                best_solution.routes[route_idx].customers = candidate_customers

    return best_solution
