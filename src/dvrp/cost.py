import math
from typing import Callable, List, Optional

from dvrp.models import Customer


def euclidean(a: Customer, b: Customer) -> float:
    """Euclidean distance between two customers (or depot represented as Customer)."""
    return math.hypot(a.x - b.x, a.y - b.y)


def make_dist_fn(
    delay_map: Optional[dict] = None,
    weather_factor: float = 1.0,
) -> Callable[[Customer, Customer], float]:
    """
    Build a distance function that incorporates:
      - delay_map  : {(id_a, id_b): multiplier} for traffic-delayed segments
      - weather_factor : global speed reduction multiplier (>= 1.0 = slower)

    Both delay_map keys are stored bidirectionally so (a,b) == (b,a).

    Returns a drop-in replacement for euclidean().
    """
    def dist(a: Customer, b: Customer) -> float:
        d = euclidean(a, b)
        if delay_map:
            d *= delay_map.get((a.id, b.id), delay_map.get((b.id, a.id), 1.0))
        return d * weather_factor

    return dist


def route_distance(
    depot: Customer,
    customers: List[Customer],
    dist_fn: Optional[Callable] = None,
) -> float:
    """
    Distance for a route: depot -> c1 -> c2 -> ... -> depot.
    Accepts an optional dist_fn for delay/weather-aware cost computation.
    Defaults to plain Euclidean distance.
    """
    if not customers:
        return 0.0

    fn = dist_fn if dist_fn is not None else euclidean
    dist = fn(depot, customers[0])
    for i in range(len(customers) - 1):
        dist += fn(customers[i], customers[i + 1])
    dist += fn(customers[-1], depot)
    return dist


def route_demand(customers: List[Customer]) -> float:
    return sum(c.demand for c in customers)


def is_capacity_feasible(customers: List[Customer], capacity: float) -> bool:
    return route_demand(customers) <= capacity