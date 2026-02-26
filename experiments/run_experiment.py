"""
experiments/run_experiment.py

PURPOSE
-------
Run a reproducible DVRP simulation and save results (plots + CSV) for analysis.

WHY YOUR PREVIOUS RUN HAD 0% ACCEPTANCE
--------------------------------------
You had too little fleet capacity compared to total demand (initial + dynamic).
That makes every new-customer insertion infeasible => Accepted=0, Rejected=all, flat cost curve.

This updated script increases VEHICLE_CAPACITY so you can *see* the algorithm working.
Later, we’ll tune capacity back down and measure rejection rate intentionally.
"""

import csv
import random
from pathlib import Path

import matplotlib.pyplot as plt

from dvrp.models import Customer, Vehicle
from dvrp.simulator import simulate


# -------------------------
# Configuration (edit here)
# -------------------------
SEED = 42

INITIAL_CUSTOMERS = 10       # customers known before simulation starts
DYNAMIC_CUSTOMERS = 20       # dynamic arrivals

DEMAND_MIN = 1
DEMAND_MAX = 5

# Simple synthetic geography
X_MIN, X_MAX = -50, 50
Y_MIN, Y_MAX = -50, 50

# Fleet
VEHICLE_COUNT = 2
VEHICLE_CAPACITY = 200   # ✅ Updated: raise capacity so events can be accepted

# Time budget per event (ms)
BUDGET_MS = 30

# Output directory
OUT_DIR = Path("experiments")


# -------------------------
# Data generation utilities
# -------------------------
def random_customer(cid: int) -> Customer:
    """Create a random customer with (x, y) and demand."""
    return Customer(
        id=cid,
        x=random.uniform(X_MIN, X_MAX),
        y=random.uniform(Y_MIN, Y_MAX),
        demand=random.randint(DEMAND_MIN, DEMAND_MAX),
    )


def save_csv(metrics, path: Path) -> None:
    """Save event-by-event metrics to CSV for reporting/analysis."""
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t", "event", "total_cost", "update_ms", "accepted", "reason"])
        for m in metrics:
            writer.writerow([m.t, m.event, m.total_cost, m.update_ms, m.accepted, m.reason])


# -------------------------
# Plotting utility
# -------------------------
def plot_and_save(series, title: str, xlabel: str, ylabel: str, out_path: Path) -> None:
    """
    Save a plot to a PNG file. (More reliable than plt.show() in VS Code terminals.)
    """
    plt.figure()
    plt.plot(series)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(out_path)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    random.seed(SEED)

    depot = Customer(0, 0, 0, 0)

    # Initial customers
    customers = [random_customer(i) for i in range(1, INITIAL_CUSTOMERS + 1)]
    initial_total_demand = sum(c.demand for c in customers)

    # Fleet
    vehicles = [Vehicle(i, capacity=VEHICLE_CAPACITY) for i in range(1, VEHICLE_COUNT + 1)]
    total_fleet_capacity = sum(v.capacity for v in vehicles)

    # Dynamic events: new customer arrivals
    start_id = INITIAL_CUSTOMERS + 1
    end_id = INITIAL_CUSTOMERS + DYNAMIC_CUSTOMERS
    events = [{"type": "new_customer", "customer": random_customer(i)} for i in range(start_id, end_id + 1)]
    dynamic_total_demand = sum(e["customer"].demand for e in events)

    # -------------------------
    # Feasibility sanity check
    # -------------------------
    print("===== Demand vs Capacity Sanity Check =====")
    print(f"Initial demand total: {initial_total_demand}")
    print(f"Dynamic demand total:  {dynamic_total_demand}")
    print(f"Total demand:          {initial_total_demand + dynamic_total_demand}")
    print(f"Fleet capacity total:  {total_fleet_capacity}")
    if initial_total_demand + dynamic_total_demand > total_fleet_capacity:
        print("WARNING: Total demand > Fleet capacity => some events MUST be rejected.")
    else:
        print("OK: Fleet capacity >= Total demand => events should be mostly accepted.")
    print("===========================================\n")

    # Run simulation
    metrics = simulate(
        depot=depot,
        customers=customers,
        vehicles=vehicles,
        events=events,
        budget_ms=BUDGET_MS,
    )

    # Summaries
    accepted = sum(1 for m in metrics if m.accepted)
    rejected = len(metrics) - accepted
    acceptance_rate = accepted / len(metrics) if metrics else 0.0

    avg_latency = sum(m.update_ms for m in metrics) / len(metrics) if metrics else 0.0
    max_latency = max((m.update_ms for m in metrics), default=0.0)

    print("===== DVRP Experiment Summary =====")
    print(f"Seed: {SEED}")
    print(f"Initial customers: {INITIAL_CUSTOMERS}")
    print(f"Dynamic events: {DYNAMIC_CUSTOMERS}")
    print(f"Vehicles: {VEHICLE_COUNT}, capacity each: {VEHICLE_CAPACITY}")
    print(f"Time budget per event: {BUDGET_MS} ms")
    print("-----------------------------------")
    print(f"Accepted: {accepted}")
    print(f"Rejected: {rejected}")
    print(f"Acceptance rate: {acceptance_rate:.2%}")
    print(f"Avg update latency: {avg_latency:.2f} ms")
    print(f"Max update latency: {max_latency:.2f} ms")
    print("===================================\n")

    # Series for plotting
    costs = [m.total_cost for m in metrics]
    latencies = [m.update_ms for m in metrics]
    acceptance_series = [1 if m.accepted else 0 for m in metrics]

    # Save plots
    plot_and_save(
        costs,
        title="Total Cost Over Dynamic Events",
        xlabel="Event Index",
        ylabel="Total Route Cost",
        out_path=OUT_DIR / "cost_plot.png",
    )

    plot_and_save(
        latencies,
        title="Update Latency (ms) Over Dynamic Events",
        xlabel="Event Index",
        ylabel="Milliseconds",
        out_path=OUT_DIR / "latency_plot.png",
    )

    plot_and_save(
        acceptance_series,
        title="Event Acceptance Over Dynamic Events (1=accepted, 0=rejected)",
        xlabel="Event Index",
        ylabel="Accepted?",
        out_path=OUT_DIR / "acceptance_plot.png",
    )

    # Save CSV
    save_csv(metrics, OUT_DIR / "metrics.csv")

    print("Saved outputs to experiments/:")
    print("- cost_plot.png")
    print("- latency_plot.png")
    print("- acceptance_plot.png")
    print("- metrics.csv")


if __name__ == "__main__":
    main()