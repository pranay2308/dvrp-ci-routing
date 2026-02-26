import math
from typing import List

from dvrp.models import Customer


def euclidean(a: Customer, b: Customer) -> float:
    """Euclidean distance between two customers (or depot represented as Customer)."""
    return math.hypot(a.x - b.x, a.y - b.y)


def route_distance(depot: Customer, customers: List[Customer]) -> float:
    """
    Distance for a route:
    depot -> c1 -> c2 -> ... -> depot
    """
    if not customers:
        return 0.0

    dist = euclidean(depot, customers[0])
    for i in range(len(customers) - 1):
        dist += euclidean(customers[i], customers[i + 1])
    dist += euclidean(customers[-1], depot)
    return dist


def route_demand(customers: List[Customer]) -> float:
    return sum(c.demand for c in customers)


def is_capacity_feasible(customers: List[Customer], capacity: float) -> bool:
    return route_demand(customers) <= capacity