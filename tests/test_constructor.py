from dvrp.models import Customer, Vehicle
from dvrp.constructors import greedy_capacity_assignment


def test_greedy_assignment_capacity_respected():
    depot = Customer(0, 0, 0, 0)

    customers = [
        Customer(1, 0, 0, 2),
        Customer(2, 0, 0, 3),
        Customer(3, 0, 0, 4),
    ]

    vehicles = [
        Vehicle(1, capacity=5),
        Vehicle(2, capacity=5),
    ]

    solution = greedy_capacity_assignment(depot, customers, vehicles)

    assert len(solution.routes) == 2
    assert len(solution.routes[0].customers) == 2
    assert len(solution.routes[1].customers) == 1