from typing import List

from dvrp.cost import is_capacity_feasible
from dvrp.models import Customer, Route, Solution, Vehicle


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
from typing import List
from dvrp.models import Customer, Vehicle, Route, Solution
from dvrp.cost import is_capacity_feasible


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