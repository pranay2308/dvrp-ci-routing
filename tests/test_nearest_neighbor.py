from dvrp.models import Customer, Vehicle
from dvrp.constructors import nearest_neighbor_constructor


def test_nearest_neighbor_builds_routes():
    depot = Customer(0, 0, 0, 0)

    customers = [
        Customer(1, 1, 0, 1),
        Customer(2, 2, 0, 1),
        Customer(3, 10, 0, 1),
    ]

    vehicles = [
        Vehicle(1, capacity=3),
    ]

    solution = nearest_neighbor_constructor(depot, customers, vehicles)

    assert len(solution.routes) == 1
    assert len(solution.routes[0].customers) == 3