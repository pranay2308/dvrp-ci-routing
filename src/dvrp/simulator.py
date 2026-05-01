import random
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from dvrp.aco import aco_constructor
from dvrp.constructors import nearest_neighbor_constructor
from dvrp.cost import is_capacity_feasible, make_dist_fn, route_distance
from dvrp.fuzzy_budget import fuzzy_time_budget, multi_fuzzy_time_budget, threshold_time_budget
from dvrp.ga_constructor import ga_constructor
from dvrp.local_search import two_opt_best_improvement
from dvrp.models import Customer, Route, Solution, Vehicle
from dvrp.repair import repair_with_time_budget


@dataclass
class SimMetrics:
    t: int
    event: str
    total_cost: float
    update_ms: float
    accepted: bool
    reason: str
    stability: float = field(default=1.0)
    fuzzy_budget_ms: float = field(default=0.0)


def total_solution_cost(
    depot: Customer,
    solution: Solution,
    dist_fn: Optional[Callable] = None,
) -> float:
    return sum(route_distance(depot, r.customers, dist_fn) for r in solution.routes)


def route_stability(old_solution: Solution, new_solution: Solution) -> float:
    """
    Fraction of customers whose route (vehicle index) did not change.
    Measures how much the plan was disrupted by the update.
    """
    old_assign: dict[int, int] = {}
    for i, route in enumerate(old_solution.routes):
        for c in route.customers:
            old_assign[c.id] = i

    new_assign: dict[int, int] = {}
    for i, route in enumerate(new_solution.routes):
        for c in route.customers:
            new_assign[c.id] = i

    common = set(old_assign) & set(new_assign)
    if not common:
        return 1.0

    unchanged = sum(1 for cid in common if old_assign[cid] == new_assign[cid])
    return unchanged / len(common)


def _route_contains_node(route: Route, node_id: int) -> bool:
    return any(c.id == node_id for c in route.customers)


def _repair_routes_two_opt(
    depot: Customer,
    solution: Solution,
    route_indices: List[int],
    dist_fn: Callable,
    budget_ms: int,
) -> Solution:
    """
    Apply 2-opt to specified routes within the time budget.

    Computes a single absolute deadline and passes it into each
    two_opt_best_improvement call so the budget is enforced inside
    the inner loop, not just between routes.
    """
    new_sol = deepcopy(solution)
    deadline = time.perf_counter() + budget_ms / 1000.0

    for idx in route_indices:
        if time.perf_counter() >= deadline:
            break
        route = new_sol.routes[idx]
        if len(route.customers) >= 4:
            improved, _ = two_opt_best_improvement(
                depot, route.customers, dist_fn, deadline=deadline
            )
            new_sol.routes[idx].customers = improved

    return new_sol


def _try_relocate_one(
    depot: Customer,
    solution: Solution,
    dist_fn: Callable,
    deadline: float,
) -> Solution:
    """
    Try to relocate a single customer from one route to another to reduce
    total cost. Scans all (source_route, customer, target_route, position)
    combinations and accepts the first improving move found before the
    deadline. Returns the improved solution, or the original if none found.

    This is a lightweight cross-route operator that adds genuine adaptivity
    beyond intra-route 2-opt: it can move customers between vehicles when
    doing so reduces total distance and respects capacity.
    """
    for src_idx, src_route in enumerate(solution.routes):
        if time.perf_counter() >= deadline:
            break
        if len(src_route.customers) <= 1:
            continue  # Never empty a route entirely
        for cust_idx, customer in enumerate(src_route.customers):
            if time.perf_counter() >= deadline:
                break
            src_without = (
                src_route.customers[:cust_idx] + src_route.customers[cust_idx + 1:]
            )
            src_cost_before = route_distance(depot, src_route.customers, dist_fn)
            src_cost_after = route_distance(depot, src_without, dist_fn)
            src_delta = src_cost_after - src_cost_before

            for tgt_idx, tgt_route in enumerate(solution.routes):
                if tgt_idx == src_idx:
                    continue
                if time.perf_counter() >= deadline:
                    break
                if not is_capacity_feasible(
                    tgt_route.customers + [customer], tgt_route.vehicle.capacity
                ):
                    continue
                tgt_cost_before = route_distance(depot, tgt_route.customers, dist_fn)
                for pos in range(len(tgt_route.customers) + 1):
                    tgt_with = (
                        tgt_route.customers[:pos]
                        + [customer]
                        + tgt_route.customers[pos:]
                    )
                    tgt_delta = route_distance(depot, tgt_with, dist_fn) - tgt_cost_before
                    if src_delta + tgt_delta < -1e-9:
                        new_sol = deepcopy(solution)
                        new_sol.routes[src_idx].customers = src_without
                        new_sol.routes[tgt_idx].customers = tgt_with
                        return new_sol
    return solution


def simulate(
    depot: Customer,
    customers: List[Customer],
    vehicles: List[Vehicle],
    events: List[Dict[str, Any]],
    budget_ms: int = 50,
    use_aco: bool = True,
    aco_kwargs: Optional[dict] = None,
    aco_rng: Optional[random.Random] = None,
    use_fuzzy_budget: bool = False,
    use_ga: bool = False,
    ga_kwargs: Optional[dict] = None,
    use_local_search: bool = True,
    use_threshold_budget: bool = False,
    use_multi_fuzzy: bool = False,
) -> List[SimMetrics]:
    """
    Adaptive CI DVRP simulator (proposed method).

    Handles three event types:
      - new_customer      : best-position insertion, then cross-route relocate
                            under remaining budget
      - traffic_delay     : apply edge slowdown, 2-opt affected routes (with
                            strict per-swap deadline); fallback to all non-empty
                            routes if segment endpoints appear in no route
      - weather_disruption: apply global speed factor, 2-opt all routes with
                            strict deadline, then cross-route relocate

    State tracked:
      delay_map      : {(id_a, id_b): multiplier} -- per-segment traffic delays
      weather_factor : float -- global speed reduction multiplier

    Parameters
    ----------
    use_fuzzy_budget      : if True, compute per-event time budget via fuzzy logic
    use_ga                : if True, use GA constructor (takes priority over use_aco)
    ga_kwargs             : keyword arguments forwarded to ga_constructor
    use_local_search      : if False, skip 2-opt and cross-route relocate (insertion only)
                            Used in ablation to isolate fuzzy budget from repair quality
    use_threshold_budget  : if True, use hard-threshold budget instead of fuzzy
                            (severity < 0.4 -> 30ms, >= 0.4 -> 80ms)
                            Overrides use_fuzzy_budget if both set.
    use_multi_fuzzy       : if True, use 3-input Mamdani FIS (severity +
                            affected_route_ratio + route_load_factor).
                            Takes priority over use_fuzzy_budget and use_threshold_budget.
    """
    if use_ga:
        kwargs = ga_kwargs or {}
        solution = ga_constructor(depot, customers, vehicles, **kwargs)
    elif use_aco:
        kwargs = aco_kwargs or {}
        solution = aco_constructor(depot, customers, vehicles, rng=aco_rng, **kwargs)
    else:
        solution = nearest_neighbor_constructor(depot, customers, vehicles)

    # Persistent disruption state
    delay_map: dict = {}
    weather_factor: float = 1.0

    metrics: List[SimMetrics] = []

    for t, event in enumerate(events):
        start = time.perf_counter()
        prev_solution = deepcopy(solution)
        accepted = False
        reason = ""

        etype = event["type"]

        # Compute effective time budget
        if use_multi_fuzzy:
            effective_budget = multi_fuzzy_time_budget(event, solution, budget_ms)
        elif use_threshold_budget:
            effective_budget = threshold_time_budget(event, budget_ms)
        elif use_fuzzy_budget:
            effective_budget = fuzzy_time_budget(event, budget_ms)
        else:
            effective_budget = budget_ms

        # Absolute deadline for this event
        event_deadline = start + effective_budget / 1000.0

        # ------------------------------------------------------------------
        # Event: new customer arrival
        # ------------------------------------------------------------------
        if etype == "new_customer":
            dist_fn = make_dist_fn(delay_map, weather_factor)
            # Insertion is a single O(K*n) scan — runs once and returns.
            solution2 = repair_with_time_budget(
                depot=depot,
                solution=solution,
                new_customer=event["customer"],
                budget_ms=effective_budget,
                dist_fn=dist_fn,
            )
            if solution2 is not None:
                solution = solution2
                accepted = True
                # Use remaining budget for a cross-route relocate move.
                if use_local_search and time.perf_counter() < event_deadline:
                    solution = _try_relocate_one(
                        depot, solution, dist_fn, event_deadline
                    )
            else:
                reason = "Repair returned None (capacity exceeded)"

        # ------------------------------------------------------------------
        # Event: traffic delay on a road segment
        # {"type": "traffic_delay", "segment": (id_a, id_b), "factor": 2.0}
        # ------------------------------------------------------------------
        elif etype == "traffic_delay":
            id_a, id_b = event["segment"]
            factor = event["factor"]
            delay_map[(id_a, id_b)] = factor
            delay_map[(id_b, id_a)] = factor  # bidirectional

            dist_fn = make_dist_fn(delay_map, weather_factor)

            if use_local_search:
                # Repair routes that contain either endpoint of the delayed segment.
                # Fallback: if neither endpoint appears in any route (e.g. segment
                # is on a road between depots), repair all non-empty routes so the
                # event never collapses to zero work.
                affected_indices = [
                    i for i, r in enumerate(solution.routes)
                    if _route_contains_node(r, id_a) or _route_contains_node(r, id_b)
                ]
                if not affected_indices:
                    affected_indices = [
                        i for i, r in enumerate(solution.routes) if r.customers
                    ]
                remaining_ms = max(0, (event_deadline - time.perf_counter()) * 1000)
                solution = _repair_routes_two_opt(
                    depot, solution, affected_indices, dist_fn, int(remaining_ms)
                )
                # Cross-route relocate under remaining budget
                if time.perf_counter() < event_deadline:
                    solution = _try_relocate_one(
                        depot, solution, dist_fn, event_deadline
                    )
            accepted = True

        # ------------------------------------------------------------------
        # Event: weather disruption (global speed reduction)
        # {"type": "weather_disruption", "factor": 1.3}
        # ------------------------------------------------------------------
        elif etype == "weather_disruption":
            weather_factor = event["factor"]
            dist_fn = make_dist_fn(delay_map, weather_factor)

            if use_local_search:
                # Repair all non-empty routes under the new cost model.
                all_indices = [
                    i for i, r in enumerate(solution.routes) if r.customers
                ]
                remaining_ms = max(0, (event_deadline - time.perf_counter()) * 1000)
                solution = _repair_routes_two_opt(
                    depot, solution, all_indices, dist_fn, int(remaining_ms)
                )
                # Cross-route relocate under remaining budget
                if time.perf_counter() < event_deadline:
                    solution = _try_relocate_one(
                        depot, solution, dist_fn, event_deadline
                    )
            accepted = True

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
            fuzzy_budget_ms=float(effective_budget),
        ))

    return metrics
