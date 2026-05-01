import time
from typing import Callable, List, Optional, Tuple

from dvrp.cost import euclidean, route_distance
from dvrp.models import Customer


def two_opt_best_improvement(
    depot: Customer,
    customers: List[Customer],
    dist_fn: Optional[Callable] = None,
    deadline: Optional[float] = None,
) -> Tuple[List[Customer], float]:
    """
    2-opt best-improvement local search for a single route.

    Reverses route segments to reduce total distance.
    Accepts an optional dist_fn for delay/weather-aware cost computation
    and an optional absolute deadline (time.perf_counter() value) that
    stops the search mid-pass when exceeded, enforcing the time budget
    strictly within a single route's inner loop.

    Args:
        depot    : The depot (starting/ending point)
        customers: The list of customers in the current route order
        dist_fn  : Optional distance function (default: Euclidean)
        deadline : Optional absolute time limit (perf_counter value).
                   When provided, exits as soon as the clock passes this
                   value so the budget is enforced inside the route search,
                   not just between routes.

    Returns:
        (improved_order, best_distance)
    """
    best = customers[:]
    best_cost = route_distance(depot, best, dist_fn)

    n = len(best)
    if n < 4:
        return best, best_cost

    improved = True
    while improved:
        improved = False
        for i in range(0, n - 2):
            for k in range(i + 2, n):
                if deadline is not None and time.perf_counter() >= deadline:
                    return best, best_cost
                candidate = best[:i] + list(reversed(best[i:k + 1])) + best[k + 1:]
                cand_cost = route_distance(depot, candidate, dist_fn)
                if cand_cost < best_cost - 1e-9:
                    best = candidate
                    best_cost = cand_cost
                    improved = True

    return best, best_cost
