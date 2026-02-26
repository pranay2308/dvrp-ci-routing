from dvrp.models import Customer
from dvrp.cost import euclidean, route_distance, is_capacity_feasible


def test_euclidean_distance():
    a = Customer(0, 0, 0, 0)
    b = Customer(1, 3, 4, 0)
    assert euclidean(a, b) == 5.0


def test_route_distance_triangle():
    depot = Customer(0, 0, 0, 0)
    c1 = Customer(1, 3, 0, 1)
    c2 = Customer(2, 3, 4, 1)
    # depot->c1 = 3, c1->c2 = 4, c2->depot = 5 => total 12
    assert route_distance(depot, [c1, c2]) == 12.0


def test_capacity_feasible():
    customers = [Customer(1, 0, 0, 2), Customer(2, 0, 0, 3)]
    assert is_capacity_feasible(customers, capacity=5)
    assert not is_capacity_feasible(customers, capacity=4)