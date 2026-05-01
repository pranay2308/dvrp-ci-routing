"""
experiments/benchmark_experiment.py

Benchmark experiment using real Solomon VRPTW instances.

Runs three methods side-by-side as described in the proposal:
    1. Proposed   : ACO initial construction + time-budgeted incremental repair
    2. Full Re-opt: Nearest-neighbor full rebuild on every event (no time limit)
    3. Static     : Initial plan only — costs updated but routes never changed

All three dynamic event types from the proposal are included:
    - new_customer       : arriving order requests
    - traffic_delay      : segment-level slowdown (e.g. accident, construction)
    - weather_disruption : global speed reduction (e.g. rain, snow)

Metrics compared (per proposal Section V):
    - Total routing cost over dynamic events
    - Average / max computation time per update (ms)
    - Solution stability (fraction of customers staying on same route)
    - Event acceptance rate

Usage:
    cd dvrp-ci-routing
    python experiments/benchmark_experiment.py
"""

import csv
import random
from pathlib import Path

import matplotlib.pyplot as plt

from dvrp.baseline import simulate_full_reopt, simulate_static
from dvrp.data_loader import load_solomon_csv, make_fleet
from dvrp.ga_constructor import ga_constructor
from dvrp.simulator import simulate


# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------

INSTANCE_PATH = Path("solomon_dataset/C1/C101.csv")

DYNAMIC_CUSTOMER_RATIO = 0.30   # 30% of customers arrive dynamically
BUDGET_MS = 50                  # time budget per event (proposed method)
SEED = 42

# ACO parameters for initial construction
ACO_KWARGS = dict(n_ants=10, n_iterations=20, alpha=1.0, beta=2.0, rho=0.5)

# GA parameters for initial construction
GA_KWARGS = dict(pop_size=30, n_generations=50, mutation_rate=0.15, seed=SEED)

OUT_DIR = Path("experiments/results")


# -----------------------------------------------------------------------
# Event generation
# -----------------------------------------------------------------------

def build_event_stream(dynamic_customers, all_customers, seed):
    """
    Build a mixed event stream with all three event types from the proposal:
      - new_customer       : one per dynamic customer
      - traffic_delay      : one event, injected after ~33% of customer arrivals
      - weather_disruption : one event, injected after ~50% of customer arrivals

    Event positions are seeded for reproducibility.
    """
    rng = random.Random(seed + 1)
    n = len(dynamic_customers)
    total = n + 2  # 2 disruption events

    # Build base customer events
    events = [{"type": "new_customer", "customer": c} for c in dynamic_customers]

    # Pick two customer IDs from the initial set for the traffic delay segment
    segment_nodes = rng.sample([c.id for c in all_customers[:10]], 2)

    # Inject traffic delay after first third of customer events
    insert_traffic = n // 3
    events.insert(insert_traffic, {
        "type": "traffic_delay",
        "segment": tuple(segment_nodes),
        "factor": 2.0,   # travel time on this segment doubles
    })

    # Inject weather disruption after half of customer events (shifted by 1)
    insert_weather = n // 2 + 1
    events.insert(insert_weather, {
        "type": "weather_disruption",
        "factor": 1.3,   # all travel 30% slower (rain / snow)
    })

    return events


def split_customers(customers, dynamic_ratio, seed):
    rng = random.Random(seed)
    shuffled = customers[:]
    rng.shuffle(shuffled)
    split = int(len(shuffled) * (1 - dynamic_ratio))
    return shuffled[:split], shuffled[split:]


# -----------------------------------------------------------------------
# Output helpers
# -----------------------------------------------------------------------

def save_comparison_csv(results: dict, path: Path):
    methods = list(results.keys())
    n_events = len(results[methods[0]])
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["t", "event_type"]
            + [f"{m}_cost" for m in methods]
            + [f"{m}_ms" for m in methods]
            + [f"{m}_accepted" for m in methods]
            + [f"{m}_stability" for m in methods]
        )
        for i in range(n_events):
            row = [i, results[methods[0]][i].event]
            for m in methods:
                row.append(round(results[m][i].total_cost, 2))
            for m in methods:
                row.append(round(results[m][i].update_ms, 3))
            for m in methods:
                row.append(int(results[m][i].accepted))
            for m in methods:
                row.append(round(results[m][i].stability, 3))
            writer.writerow(row)


def plot_comparison(results, metric_attr, title, ylabel, filename, out_dir,
                    event_list=None):
    plt.figure(figsize=(11, 4))
    for method, metrics in results.items():
        values = [getattr(m, metric_attr) for m in metrics]
        plt.plot(values, label=method, marker="o", markersize=3)

    # Mark disruption events with vertical lines
    if event_list:
        for i, ev in enumerate(event_list):
            if ev["type"] == "traffic_delay":
                plt.axvline(x=i, color="orange", linestyle="--",
                            alpha=0.6, label="Traffic delay" if i == next(
                                j for j, e in enumerate(event_list)
                                if e["type"] == "traffic_delay") else "")
            elif ev["type"] == "weather_disruption":
                plt.axvline(x=i, color="blue", linestyle=":",
                            alpha=0.6, label="Weather disruption" if i == next(
                                j for j, e in enumerate(event_list)
                                if e["type"] == "weather_disruption") else "")

    plt.title(title)
    plt.xlabel("Event Index")
    plt.ylabel(ylabel)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / filename, dpi=150)
    plt.close()


def print_summary(method, metrics):
    costs     = [m.total_cost for m in metrics]
    latencies = [m.update_ms  for m in metrics]
    stabs     = [m.stability  for m in metrics]
    accepted  = sum(1 for m in metrics if m.accepted)
    n = len(metrics)

    print(f"\n  [{method}]")
    print(f"    Final cost          : {costs[-1]:.2f}")
    print(f"    Avg update latency  : {sum(latencies)/n:.3f} ms")
    print(f"    Max update latency  : {max(latencies):.3f} ms")
    print(f"    Acceptance rate     : {accepted}/{n} ({accepted/n*100:.1f}%)")
    print(f"    Avg stability       : {sum(stabs)/n:.3f}")


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(SEED)

    # Load instance
    print(f"Loading instance: {INSTANCE_PATH}")
    depot, all_customers = load_solomon_csv(INSTANCE_PATH)
    vehicles = make_fleet(INSTANCE_PATH)
    print(f"  Customers : {len(all_customers)}")
    print(f"  Vehicles  : {len(vehicles)} x capacity {vehicles[0].capacity}")

    # Split initial / dynamic
    initial_customers, dynamic_customers = split_customers(
        all_customers, DYNAMIC_CUSTOMER_RATIO, SEED
    )

    # Build mixed event stream (customer + traffic + weather)
    events = build_event_stream(dynamic_customers, all_customers, SEED)

    customer_events = sum(1 for e in events if e["type"] == "new_customer")
    disruption_events = len(events) - customer_events

    print(f"\n  Initial customers   : {len(initial_customers)}")
    print(f"  Dynamic customers   : {customer_events}")
    print(f"  Disruption events   : {disruption_events} "
          f"(traffic delay + weather)")
    print(f"  Total events        : {len(events)}")
    print(f"  Time budget         : {BUDGET_MS} ms / event (proposed)\n")

    # Run all methods
    print("Running: ACO+Repair (fixed budget)...")
    proposed_aco = simulate(
        depot=depot,
        customers=initial_customers,
        vehicles=vehicles,
        events=events,
        budget_ms=BUDGET_MS,
        use_aco=True,
        aco_kwargs=ACO_KWARGS,
    )

    print("Running: FACI-DVRP (ACO + Fuzzy Budget + Repair)...")
    proposed_aco_fuzzy = simulate(
        depot=depot,
        customers=initial_customers,
        vehicles=vehicles,
        events=events,
        budget_ms=BUDGET_MS,
        use_aco=True,
        aco_kwargs=ACO_KWARGS,
        use_fuzzy_budget=True,
    )

    print("Running: GA + Fuzzy Budget + Repair...")
    proposed_ga = simulate(
        depot=depot,
        customers=initial_customers,
        vehicles=vehicles,
        events=events,
        budget_ms=BUDGET_MS,
        use_ga=True,
        ga_kwargs=GA_KWARGS,
        use_fuzzy_budget=True,
    )

    print("Running: Full Re-optimization baseline...")
    reopt = simulate_full_reopt(
        depot=depot,
        customers=initial_customers,
        vehicles=vehicles,
        events=events,
    )

    print("Running: Static baseline...")
    static = simulate_static(
        depot=depot,
        customers=initial_customers,
        vehicles=vehicles,
        events=events,
    )

    results = {
        "ACO+Repair (fixed budget)":     proposed_aco,
        "FACI-DVRP (ACO+Fuzzy+Repair)":  proposed_aco_fuzzy,
        "GA+Fuzzy+Repair":               proposed_ga,
        "Full Re-opt (NN)":              reopt,
        "Static":                         static,
    }

    # Print summaries
    print("\n===== Benchmark Results =====")
    print(f"  Instance : {INSTANCE_PATH.name}")
    print(f"  Seed     : {SEED}")
    for method, metrics in results.items():
        print_summary(method, metrics)

    # Save plots
    plot_comparison(
        results, "total_cost",
        title=f"Total Routing Cost — {INSTANCE_PATH.name}",
        ylabel="Total Cost (Euclidean, with delays)",
        filename="cost_comparison.png",
        out_dir=OUT_DIR, event_list=events,
    )
    plot_comparison(
        results, "update_ms",
        title=f"Update Latency per Event — {INSTANCE_PATH.name}",
        ylabel="Milliseconds",
        filename="latency_comparison.png",
        out_dir=OUT_DIR, event_list=events,
    )
    plot_comparison(
        results, "stability",
        title=f"Route Stability per Event — {INSTANCE_PATH.name}",
        ylabel="Stability (1 = no change)",
        filename="stability_comparison.png",
        out_dir=OUT_DIR, event_list=events,
    )

    save_comparison_csv(results, OUT_DIR / "benchmark_metrics.csv")

    print(f"\nOutputs saved to {OUT_DIR}/")
    print("  cost_comparison.png")
    print("  latency_comparison.png")
    print("  stability_comparison.png")
    print("  benchmark_metrics.csv")


if __name__ == "__main__":
    main()
