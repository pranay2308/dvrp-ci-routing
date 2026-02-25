from dvrp.models import Customer
from dvrp.cost import route_distance
from dvrp.local_search import two_opt_best_improvement


def test_two_opt_improves_or_keeps_cost():
    depot = Customer(0, 0, 0, 0)

    # A "bad" order that should be improvable
    customers = [
        Customer(1, 0, 10, 1),
        Customer(2, 10, 0, 1),
        Customer(3, 0, -10, 1),
        Customer(4, -10, 0, 1),
    ]

    before = route_distance(depot, customers)
    improved_order, after = two_opt_best_improvement(depot, customers)

    assert set(c.id for c in improved_order) == set(c.id for c in customers)
    assert after <= before
    