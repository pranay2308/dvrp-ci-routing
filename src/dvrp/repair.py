from typing import Optional

from dvrp.dynamic import insert_customer_best_position
from dvrp.models import Customer, Solution
from dvrp.time_budget import run_with_time_budget


def repair_with_time_budget(
    depot: Customer,
    solution: Solution,
    new_customer: Customer,
    budget_ms: int,
) -> Optional[Solution]:
    """
    Try to insert a new customer within a time budget.
    Returns a repaired solution or None if infeasible.
    """

    def step() -> Optional[Solution]:
        return insert_customer_best_position(depot, solution, new_customer)

    def accept(candidate: Optional[Solution]) -> bool:
        return candidate is not None

    return run_with_time_budget(budget_ms, step, accept)
