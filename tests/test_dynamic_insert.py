from dvrp.models import Customer, Vehicle, Route, Solution
from dvrp.dynamic import insert_customer_best_position


def test_dynamic_insert_adds_customer():
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

    updated = insert_customer_best_position(depot, solution, new_customer)

    assert updated is not None
    assert any(c.id == 3 for c in updated.routes[0].customers)
    