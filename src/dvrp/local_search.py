from typing import List, Tuple
from dvrp.models import Customer
from dvrp.cost import route_distance


def two_opt_best_improvement(
    depot: Customer,
    customers: List[Customer],
) -> Tuple[List[Customer], float]:
    """
    2-opt best-improvement local search for a single route.
    
    This algorithm improves a route by reversing segments of the route
    to reduce the total distance. It uses the best improvement strategy,
    meaning it always makes the move that results in the maximum cost reduction.
    
    Args:
        depot: The depot (starting/ending point)
        customers: The list of customers in the current route order
        
    Returns:
        A tuple of (improved_order, best_distance) where improved_order
        is the reordered list and best_distance is the route distance.
    """
    best = customers[:]
    best_cost = route_distance(depot, best)

    n = len(best)
    if n < 4:
        return best, best_cost

    improved = True
    while improved:
        improved = False
        for i in range(0, n - 2):
            for k in range(i + 2, n):
                candidate = best[:i] + list(reversed(best[i:k + 1])) + best[k + 1:]
                cand_cost = route_distance(depot, candidate)
                if cand_cost < best_cost - 1e-9:
                    best = candidate
                    best_cost = cand_cost
                    improved = True
    
    return best, best_cost
