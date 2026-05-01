"""
src/dvrp/ga_constructor.py

Genetic Algorithm (GA) constructor for VRP initial route building.

This implements the second CI metaheuristic in the FACI-DVRP framework,
providing a GA alternative to ACO for building initial solutions.

Encoding
--------
  Chromosome : permutation of customer IDs (giant-tour representation)
  Decoding   : split tour into vehicle routes greedily by capacity constraint

Operators
---------
  Selection  : binary tournament (k=2) -- simple, effective
  Crossover  : Order Crossover (OX) -- preserves relative order of customers
  Mutation   : swap mutation -- randomly swap two positions in the chromosome
  Elitism    : top-1 individual always survives to next generation

Fitness
-------
  Total route distance of the decoded solution (lower is better).
  Infeasible chromosomes (unserved customers) penalized by +1e6 per customer.
"""

import random
from copy import deepcopy
from typing import List, Optional, Tuple

from dvrp.cost import euclidean, is_capacity_feasible, route_distance
from dvrp.models import Customer, Route, Solution, Vehicle


# ---------------------------------------------------------------------------
# Chromosome encoding / decoding
# ---------------------------------------------------------------------------

def _decode(
    chromosome: List[int],
    id_to_customer: dict,
    depot: Customer,
    vehicles: List[Vehicle],
) -> Tuple[Solution, float]:
    """
    Decode a customer-ID permutation into a VRP Solution.

    Greedily fills vehicles in order, starting a new route when capacity
    would be exceeded.

    Returns
    -------
    (solution, total_distance)
    """
    solution = Solution()
    unserved: List[Customer] = [id_to_customer[cid] for cid in chromosome]

    remaining = unserved[:]
    for vehicle in vehicles:
        route = Route(vehicle)
        current_demand = 0.0

        still_remaining = []
        for c in remaining:
            if current_demand + c.demand <= vehicle.capacity:
                route.add_customer(c)
                current_demand += c.demand
            else:
                still_remaining.append(c)

        solution.add_route(route)
        remaining = still_remaining

        if not remaining:
            break

    # Add empty routes for unused vehicles
    used = len(solution.routes)
    for vehicle in vehicles[used:]:
        solution.add_route(Route(vehicle))

    # Fitness: total distance + penalty for unserved customers
    total_dist = sum(route_distance(depot, r.customers) for r in solution.routes)
    penalty = len(remaining) * 1e6
    return solution, total_dist + penalty


# ---------------------------------------------------------------------------
# Genetic operators
# ---------------------------------------------------------------------------

def _tournament_select(
    population: List[List[int]],
    fitnesses: List[float],
    k: int = 2,
    rng: random.Random = None,
) -> List[int]:
    """Binary tournament selection."""
    if rng is None:
        rng = random
    contestants = rng.sample(range(len(population)), k)
    winner = min(contestants, key=lambda i: fitnesses[i])
    return population[winner][:]


def _ox_crossover(
    parent1: List[int],
    parent2: List[int],
    rng: random.Random,
) -> List[int]:
    """
    Order Crossover (OX):
    1. Copy a random sub-segment from parent1 into the child.
    2. Fill remaining positions with values from parent2 in order,
       skipping values already in the child.
    """
    n = len(parent1)
    a, b = sorted(rng.sample(range(n), 2))
    child = [None] * n
    child[a:b+1] = parent1[a:b+1]
    segment = set(parent1[a:b+1])

    fill = [x for x in parent2 if x not in segment]
    idx = 0
    for i in range(n):
        if child[i] is None:
            child[i] = fill[idx]
            idx += 1
    return child


def _swap_mutate(chromosome: List[int], rate: float, rng: random.Random) -> List[int]:
    """Swap mutation: randomly swap two positions with probability `rate`."""
    c = chromosome[:]
    if rng.random() < rate and len(c) >= 2:
        i, j = rng.sample(range(len(c)), 2)
        c[i], c[j] = c[j], c[i]
    return c


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ga_constructor(
    depot: Customer,
    customers: List[Customer],
    vehicles: List[Vehicle],
    pop_size: int = 30,
    n_generations: int = 50,
    mutation_rate: float = 0.15,
    tournament_k: int = 2,
    seed: Optional[int] = None,
) -> Solution:
    """
    Build an initial VRP solution using a Genetic Algorithm.

    Parameters
    ----------
    depot         : depot node
    customers     : list of customers to serve
    vehicles      : available fleet
    pop_size      : number of individuals in the population
    n_generations : number of GA generations
    mutation_rate : probability of swap mutation per individual
    tournament_k  : tournament size for selection
    seed          : random seed for reproducibility

    Returns
    -------
    Best Solution found across all generations.
    """
    if not customers:
        sol = Solution()
        for v in vehicles:
            sol.add_route(Route(v))
        return sol

    rng = random.Random(seed)
    id_to_customer = {c.id: c for c in customers}
    cust_ids = [c.id for c in customers]

    # Initialize population with random permutations
    population = [rng.sample(cust_ids, len(cust_ids)) for _ in range(pop_size)]

    # Evaluate initial population
    decoded = [_decode(chrom, id_to_customer, depot, vehicles) for chrom in population]
    fitnesses = [f for _, f in decoded]

    best_idx = min(range(pop_size), key=lambda i: fitnesses[i])
    best_solution = deepcopy(decoded[best_idx][0])
    best_fitness = fitnesses[best_idx]

    for _ in range(n_generations):
        new_population: List[List[int]] = []

        # Elitism: carry forward best individual
        new_population.append(population[best_idx][:])

        # Generate rest of new population
        while len(new_population) < pop_size:
            p1 = _tournament_select(population, fitnesses, tournament_k, rng)
            p2 = _tournament_select(population, fitnesses, tournament_k, rng)
            child = _ox_crossover(p1, p2, rng)
            child = _swap_mutate(child, mutation_rate, rng)
            new_population.append(child)

        population = new_population

        # Evaluate new population
        decoded = [_decode(chrom, id_to_customer, depot, vehicles) for chrom in population]
        fitnesses = [f for _, f in decoded]

        gen_best_idx = min(range(pop_size), key=lambda i: fitnesses[i])
        if fitnesses[gen_best_idx] < best_fitness:
            best_fitness = fitnesses[gen_best_idx]
            best_solution = deepcopy(decoded[gen_best_idx][0])
            best_idx = gen_best_idx
        else:
            best_idx = gen_best_idx

    return best_solution
