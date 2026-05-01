"""
src/dvrp/aco.py

Ant Colony Optimization (ACO) constructor for VRP initial route building.

This implements the proposal requirement:
    "an initial feasible routing solution is generated using a CI metaheuristic
     such as a Genetic Algorithm or Ant Colony Optimization."

Algorithm:
  1. Initialize pheromone matrix tau[i][j] = tau_0 for all node pairs.
  2. For each iteration, each ant builds a complete VRP solution:
       - Repeatedly select the next customer using a probabilistic rule
         based on pheromone (tau) and distance-based heuristic (eta).
       - Respects vehicle capacity constraints.
       - Opens a new vehicle route when the current route is full.
  3. Evaporate pheromones, then deposit on the iteration-best solution's edges.
  4. Return the globally best solution found.
"""

import random as _random_module
from copy import deepcopy
from typing import Callable, List, Optional, Union

# Type alias for either random.Random instance or the module itself
_RNG = Union[_random_module.Random, type(_random_module)]

from dvrp.cost import euclidean, is_capacity_feasible, route_distance
from dvrp.models import Customer, Route, Solution, Vehicle


def aco_constructor(
    depot: Customer,
    customers: List[Customer],
    vehicles: List[Vehicle],
    n_ants: int = 10,
    n_iterations: int = 30,
    alpha: float = 1.0,   # pheromone importance
    beta: float = 2.0,    # heuristic (distance) importance
    rho: float = 0.5,     # evaporation rate
    tau_0: float = 1.0,   # initial pheromone level
    rng: Optional[_random_module.Random] = None,
) -> Solution:
    """
    Build an initial VRP solution using Ant Colony Optimization.

    Parameters
    ----------
    depot       : depot node
    customers   : list of customers to serve
    vehicles    : available fleet
    n_ants      : number of ants per iteration
    n_iterations: number of ACO iterations
    alpha       : pheromone trail exponent
    beta        : heuristic (1/distance) exponent
    rho         : pheromone evaporation rate (0 < rho < 1)
    tau_0       : initial pheromone value on all edges

    Returns
    -------
    Best Solution found across all iterations.
    """
    # Use provided rng or fall back to the global random module
    _rng = rng if rng is not None else _random_module

    if not customers:
        sol = Solution()
        for v in vehicles:
            sol.add_route(Route(v))
        return sol

    # Build lookup: id -> node
    id_to_node: dict[int, Customer] = {depot.id: depot}
    for c in customers:
        id_to_node[c.id] = c

    all_ids = [depot.id] + [c.id for c in customers]

    # Pheromone matrix: tau[(i, j)]
    tau: dict[tuple, float] = {
        (i, j): tau_0
        for i in all_ids
        for j in all_ids
        if i != j
    }

    # Heuristic matrix: eta[(i, j)] = 1 / distance(i, j)
    eta: dict[tuple, float] = {}
    for i in all_ids:
        for j in all_ids:
            if i != j:
                d = euclidean(id_to_node[i], id_to_node[j])
                eta[(i, j)] = 1.0 / max(d, 1e-9)

    best_solution: Optional[Solution] = None
    best_cost = float("inf")

    for _ in range(n_iterations):
        ant_solutions: list[tuple[Solution, float]] = []

        for _ in range(n_ants):
            sol = _build_ant_solution(
                depot, customers, vehicles, id_to_node, tau, eta, alpha, beta, _rng
            )
            cost = sum(route_distance(depot, r.customers) for r in sol.routes)
            ant_solutions.append((sol, cost))

            if cost < best_cost:
                best_cost = cost
                best_solution = deepcopy(sol)

        # Pheromone evaporation
        for key in tau:
            tau[key] = max(tau[key] * (1.0 - rho), 1e-9)

        # Deposit pheromone on iteration-best solution's edges
        iter_sol, iter_cost = min(ant_solutions, key=lambda x: x[1])
        deposit = 1.0 / iter_cost if iter_cost > 0 else 1.0

        for route in iter_sol.routes:
            if not route.customers:
                continue
            prev_id = depot.id
            for c in route.customers:
                tau[(prev_id, c.id)] = tau.get((prev_id, c.id), tau_0) + deposit
                prev_id = c.id
            tau[(prev_id, depot.id)] = tau.get((prev_id, depot.id), tau_0) + deposit

    return best_solution  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_ant_solution(
    depot: Customer,
    customers: List[Customer],
    vehicles: List[Vehicle],
    id_to_node: dict,
    tau: dict,
    eta: dict,
    alpha: float,
    beta: float,
    rng=None,
) -> Solution:
    """
    Build one complete VRP solution for a single ant.

    All vehicles are added to the solution (even if empty) so that
    dynamic insertions can open new routes for arriving customers.
    """
    unassigned = customers.copy()
    solution = Solution()

    for vehicle in vehicles:
        route = Route(vehicle)

        if unassigned:
            current_id = depot.id
            current_demand = 0.0

            while unassigned:
                feasible = [
                    c for c in unassigned
                    if current_demand + c.demand <= vehicle.capacity
                ]
                if not feasible:
                    break

                chosen = _select_next(current_id, feasible, tau, eta, alpha, beta, rng)
                route.add_customer(chosen)
                unassigned.remove(chosen)
                current_demand += chosen.demand
                current_id = chosen.id

        solution.add_route(route)

    return solution


def _select_next(
    current_id: int,
    feasible: List[Customer],
    tau: dict,
    eta: dict,
    alpha: float,
    beta: float,
    rng=None,
) -> Customer:
    """
    Probabilistic selection of next customer using ACO rule:
        P(j) = [tau(i,j)^alpha * eta(i,j)^beta] / sum_k[...]
    """
    _rng = rng if rng is not None else _random_module
    weights = [
        (tau.get((current_id, c.id), 1e-9) ** alpha)
        * (eta.get((current_id, c.id), 1e-9) ** beta)
        for c in feasible
    ]
    total = sum(weights)
    if total == 0:
        return _rng.choice(feasible)

    probs = [w / total for w in weights]
    r = _rng.random()
    cumsum = 0.0
    for c, p in zip(feasible, probs):
        cumsum += p
        if r <= cumsum:
            return c
    return feasible[-1]
