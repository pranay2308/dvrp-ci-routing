from dvrp.models import Customer, Vehicle
from dvrp.simulator import simulate


def test_simulator_runs():
    depot = Customer(0, 0, 0, 0)

    customers = [
        Customer(1, 0, 10, 2),
        Customer(2, 10, 0, 2),
    ]

    vehicles = [
        Vehicle(1, capacity=10),
    ]

    events = [
        {"type": "new_customer", "customer": Customer(3, 5, 5, 2)},
        {"type": "new_customer", "customer": Customer(4, -5, 5, 2)},
    ]

    metrics = simulate(depot, customers, vehicles, events, budget_ms=10)

    assert len(metrics) == 2
    assert all(m.total_cost > 0 for m in metrics)
    assert all(m.update_ms >= 0 for m in metrics)

    # New: ensure we log outcomes
    assert all(hasattr(m, "accepted") for m in metrics)
    assert all(hasattr(m, "reason") for m in metrics)