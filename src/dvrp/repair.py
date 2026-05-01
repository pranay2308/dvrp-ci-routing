from typing import Callable, Optional

from dvrp.dynamic import insert_customer_best_position
from dvrp.models import Customer, Solution


def repair_with_time_budget(
    depot: Customer,
    solution: Solution,
    new_customer: Customer,
    budget_ms: int,
    dist_fn: Optional[Callable] = None,
) -> Optional[Solution]:
    """
    Insert a new customer into the best feasible position.

    Insertion is a single deterministic O(K*n) scan — running it repeatedly
    inside a time-budget loop produces the same result every iteration.
    This function runs the scan once and returns immediately, leaving the
    remaining budget available for cross-route improvement in the caller.

    Returns the repaired solution or None if no feasible position exists.
    """
    return insert_customer_best_position(depot, solution, new_customer, dist_fn)
