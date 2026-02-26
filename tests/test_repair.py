from dvrp.models import Customer, Vehicle, Route, Solution
from dvrp.repair import repair_with_time_budget


def test_repair_pipeline_runs():
    depot = Customer(0, 0, 0, 0)

    vehicle = Vehicle(1, capacity=10)
    route = Route(vehicle)
    route.customers = [
        Customer(1, 0, 10, 2),
        Customer(2, 10, 0, 2),
    ]

    solution = Solution()
    solution.add_route(route)

    new_customer = Customer(3, 5, 5, 2)

    repaired = repair_with_time_budget(
        depot,
        solution,
        new_customer,
        budget_ms=20,
    )

    assert repaired is not None
    assert any(c.id == 3 for c in repaired.routes[0].customers)
    