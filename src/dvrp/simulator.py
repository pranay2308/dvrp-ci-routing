import time
from dataclasses import dataclass
from typing import Any, Dict, List

from dvrp.models import Customer, Vehicle, Solution
from dvrp.cost import route_distance
from dvrp.repair import repair_with_time_budget
from dvrp.constructors import nearest_neighbor_constructor


@dataclass
class SimMetrics:
    t: int
    event: str
    total_cost: float
    update_ms: float
    accepted: bool
    reason: str


def total_solution_cost(depot: Customer, solution: Solution) -> float:
    return sum(route_distance(depot, r.customers) for r in solution.routes)


def simulate(
    depot: Customer,
    customers: List[Customer],
    vehicles: List[Vehicle],
    events: List[Dict[str, Any]],
    budget_ms: int = 50,
) -> List[SimMetrics]:
    """
    Simple DVRP simulator:
    - Build initial plan
    - Apply events sequentially
    - Repair using time-budgeted repair pipeline
    - Record metrics
    """
    solution = nearest_neighbor_constructor(depot, customers, vehicles)
    metrics: List[SimMetrics] = []

    for t, event in enumerate(events):
        start = time.perf_counter()
        accepted = False
        reason = ""

        if event["type"] == "new_customer":
            solution2 = repair_with_time_budget(
                depot=depot,
                solution=solution,
                new_customer=event["customer"],
                budget_ms=budget_ms,
            )
            if solution2 is not None:
                solution = solution2
                accepted = True
            else:
                reason = "Repair returned None (infeasible)"

        end = time.perf_counter()
        update_ms = (end - start) * 1000.0
        cost = total_solution_cost(depot, solution)

        metrics.append(SimMetrics(
            t=t,
            event=event["type"],
            total_cost=cost,
            update_ms=update_ms,
            accepted=accepted,
            reason=reason,
        ))

    return metrics
