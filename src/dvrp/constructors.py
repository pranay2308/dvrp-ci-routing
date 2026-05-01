from typing import Callable, List, Optional

from dvrp.models import Customer, Vehicle, Route, Solution
from dvrp.cost import is_capacity_feasible, euclidean


def nearest_neighbor_constructor(
    depot: Customer,
    customers: List[Customer],
    vehicles: List[Vehicle],
    dist_fn: Optional[Callable] = None,
) -> Solution:
    """
    Greedy nearest neighbor VRP constructor.
    Builds routes by repeatedly selecting the closest feasible customer.
    """

    unassigned = customers.copy()
    solution = Solution()

    for vehicle in vehicles:
        route = Route(vehicle)
        current_location = depot

        while unassigned:
            # Filter feasible customers
            feasible = [
                c for c in unassigned
                if is_capacity_feasible(route.customers + [c], vehicle.capacity)
            ]

            if not feasible:
                break

            # Choose nearest feasible customer
            _dist = dist_fn if dist_fn is not None else euclidean
            next_customer = min(
                feasible,
                key=lambda c: _dist(current_location, c)
            )

            route.add_customer(next_customer)
            unassigned.remove(next_customer)
            current_location = next_customer

        # Always add route (even if empty) so dynamic insertions can use
        # unused vehicles when new customers arrive.
        solution.add_route(route)

    return solution


def greedy_capacity_assignment(
    depot: Customer,
    customers: List[Customer],
    vehicles: List[Vehicle],
) -> Solution:
    """
    Simple greedy assignment:
    Fill vehicles sequentially until capacity reached.
    """
    solution = Solution()
    customer_index = 0

    for vehicle in vehicles:
        route = Route(vehicle)
        while customer_index < len(customers):
            candidate = customers[customer_index]
            temp_customers = route.customers + [candidate]

            if is_capacity_feasible(temp_customers, vehicle.capacity):
                route.add_customer(candidate)
                customer_index += 1
            else:
                break

        solution.add_route(route)

        if customer_index >= len(customers):
            break

    return solution