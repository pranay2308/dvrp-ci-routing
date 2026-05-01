"""
src/dvrp/baseline.py

Two comparison baselines required by the proposal:

1. Static baseline
   - Never updates the routing plan after the initial solution.
   - Every dynamic event is "rejected" (no route change).
   - Costs are re-evaluated under current delay/weather conditions so the
     cost curve reflects real-world degradation even without adaptation.

2. Full re-optimization baseline
   - On every new_customer event: rebuilds entire solution from scratch (NN).
   - On traffic_delay / weather_disruption: re-runs NN on current customer set.
   - No time budget constraint.
   - Represents maximum solution quality at maximum computational cost.

Both return List[SimMetrics] for direct comparison with the adaptive
CI approach in simulator.py.
"""

import time
from copy import deepcopy
from typing import Any, Callable, Dict, List

from dvrp.constructors import nearest_neighbor_constructor
from dvrp.cost import make_dist_fn, route_distance
from dvrp.models import Customer, Solution, Vehicle
from dvrp.simulator import SimMetrics, route_stability, total_solution_cost


# ---------------------------------------------------------------------------
# Static baseline
# ---------------------------------------------------------------------------

def simulate_static(
    depot: Customer,
    customers: List[Customer],
    vehicles: List[Vehicle],
    events: List[Dict[str, Any]],
    constructor_fn: Callable = nearest_neighbor_constructor,
) -> List[SimMetrics]:
    """
    Static baseline: build once, never update routes.

    All dynamic events are rejected. Costs are re-evaluated under the
    current delay/weather state so the cost curve shows real degradation.
    """
    solution = constructor_fn(depot, customers, vehicles)

    delay_map: dict = {}
    weather_factor: float = 1.0
    metrics: List[SimMetrics] = []

    for t, event in enumerate(events):
        etype = event["type"]
        accepted = False
        reason = "Static baseline: no route updates performed"

        if etype == "traffic_delay":
            id_a, id_b = event["segment"]
            factor = event["factor"]
            delay_map[(id_a, id_b)] = factor
            delay_map[(id_b, id_a)] = factor
        elif etype == "weather_disruption":
            weather_factor = event["factor"]

        dist_fn = make_dist_fn(delay_map, weather_factor)
        cost = total_solution_cost(depot, solution, dist_fn)

        metrics.append(SimMetrics(
            t=t,
            event=etype,
            total_cost=cost,
            update_ms=0.0,
            accepted=accepted,
            reason=reason,
            stability=1.0,
        ))

    return metrics


# ---------------------------------------------------------------------------
# Full re-optimization baseline
# ---------------------------------------------------------------------------

def simulate_full_reopt(
    depot: Customer,
    customers: List[Customer],
    vehicles: List[Vehicle],
    events: List[Dict[str, Any]],
    constructor_fn: Callable = nearest_neighbor_constructor,
) -> List[SimMetrics]:
    """
    Full re-optimization baseline: rebuild entire solution on every event.

    - new_customer      : append customer, rebuild from scratch
    - traffic_delay     : update delay map, rebuild from scratch
    - weather_disruption: update weather factor, rebuild from scratch

    No time budget — always produces the best NN solution for the current
    state. Tracks actual computation time per event.
    """
    current_customers = customers.copy()
    delay_map: dict = {}
    weather_factor: float = 1.0

    dist_fn = make_dist_fn(delay_map, weather_factor)
    solution = constructor_fn(depot, current_customers, vehicles)

    metrics: List[SimMetrics] = []

    for t, event in enumerate(events):
        start = time.perf_counter()
        prev_solution = deepcopy(solution)
        etype = event["type"]
        accepted = False
        reason = ""

        if etype == "new_customer":
            current_customers.append(event["customer"])
            accepted = True
        elif etype == "traffic_delay":
            id_a, id_b = event["segment"]
            factor = event["factor"]
            delay_map[(id_a, id_b)] = factor
            delay_map[(id_b, id_a)] = factor
            accepted = True
        elif etype == "weather_disruption":
            weather_factor = event["factor"]
            accepted = True

        # Rebuild from scratch using updated customer set
        dist_fn = make_dist_fn(delay_map, weather_factor)
        solution = constructor_fn(depot, current_customers, vehicles, dist_fn=dist_fn)

        end = time.perf_counter()
        update_ms = (end - start) * 1000.0
        dist_fn = make_dist_fn(delay_map, weather_factor)
        cost = total_solution_cost(depot, solution, dist_fn)
        stability = route_stability(prev_solution, solution)

        metrics.append(SimMetrics(
            t=t,
            event=etype,
            total_cost=cost,
            update_ms=update_ms,
            accepted=accepted,
            reason=reason,
            stability=stability,
        ))

    return metrics
