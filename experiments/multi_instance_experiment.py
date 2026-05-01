"""
experiments/multi_instance_experiment.py

Multi-instance benchmark across three Solomon instance classes:
  - C101  (Clustered)  — customers in geographic groups
  - R101  (Random)     — customers uniformly distributed
  - RC101 (Mixed)      — combination of clustered and random

Running one representative from each class shows that results
generalize across different customer distributions — a standard
requirement for DVRP research papers.

Usage:
    cd dvrp-ci-routing
    python experiments/multi_instance_experiment.py

Outputs (saved to experiments/results/multi/):
    summary_table.csv      — one row per instance per method
    summary_table.txt      — formatted table ready to copy into paper
    cost_by_instance.png   — bar chart: final cost per instance
    latency_by_instance.png
"""

import csv
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from dvrp.baseline import simulate_full_reopt, simulate_static
from dvrp.data_loader import load_solomon_csv, make_fleet
from dvrp.simulator import simulate


# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------

INSTANCES = [
    ("C101", Path("solomon_dataset/C1/C101.csv"),  "Clustered"),
    ("R101", Path("solomon_dataset/R1/R101.csv"),  "Random"),
    ("RC101",Path("solomon_dataset/RC1/RC101.csv"),"Mixed"),
]

DYNAMIC_CUSTOMER_RATIO = 0.30
BUDGET_MS = 50
SEED = 42

ACO_KWARGS = dict(n_ants=10, n_iterations=20, alpha=1.0, beta=2.0, rho=0.5)
GA_KWARGS  = dict(pop_size=30, n_generations=50, mutation_rate=0.15, seed=SEED)

OUT_DIR = Path("experiments/results/multi")

METHODS = [
    "FACI-DVRP (ACO+Fuzzy)",
    "ACO+Multi-Fuzzy",
    "ACO+Threshold",
    "GA+Fuzzy",
    "ACO+Repair (fixed)",
    "Full Re-opt",
    "Static",
]


# -----------------------------------------------------------------------
# Helpers (same as benchmark_experiment.py)
# -----------------------------------------------------------------------

def build_event_stream(dynamic_customers, all_customers, seed):
    rng = random.Random(seed + 1)
    n = len(dynamic_customers)
    events = [{"type": "new_customer", "customer": c} for c in dynamic_customers]
    segment_nodes = rng.sample([c.id for c in all_customers[:10]], 2)
    events.insert(n // 3, {
        "type": "traffic_delay",
        "segment": tuple(segment_nodes),
        "factor": 2.0,
    })
    events.insert(n // 2 + 1, {
        "type": "weather_disruption",
        "factor": 1.3,
    })
    return events


def split_customers(customers, ratio, seed):
    rng = random.Random(seed)
    shuffled = customers[:]
    rng.shuffle(shuffled)
    split = int(len(shuffled) * (1 - ratio))
    return shuffled[:split], shuffled[split:]


def summarize(metrics):
    costs     = [m.total_cost for m in metrics]
    latencies = [m.update_ms  for m in metrics]
    stabs     = [m.stability  for m in metrics]
    accepted  = sum(1 for m in metrics if m.accepted)
    n = len(metrics)
    return {
        "final_cost":    round(costs[-1], 1),
        "avg_latency":   round(sum(latencies) / n, 1),
        "max_latency":   round(max(latencies), 1),
        "acceptance":    f"{accepted}/{n}",
        "avg_stability": round(sum(stabs) / n, 3),
    }


# -----------------------------------------------------------------------
# Run one instance
# -----------------------------------------------------------------------

def run_instance(name, path, label):
    print(f"\n{'='*60}")
    print(f"  Instance: {name}  ({label})")
    print(f"{'='*60}")

    depot, all_customers = load_solomon_csv(path)
    vehicles = make_fleet(path)
    initial, dynamic = split_customers(all_customers, DYNAMIC_CUSTOMER_RATIO, SEED)
    events = build_event_stream(dynamic, all_customers, SEED)

    print(f"  {len(initial)} initial  +  {len(dynamic)} dynamic  +  2 disruptions"
          f"  =  {len(events)} events")

    # All ACO-based methods receive a fresh random.Random(SEED) so that
    # every method starts from the same ACO initial solution, making the
    # comparison fair and results reproducible across experiments.

    print("  Running FACI-DVRP (ACO+Fuzzy)...")
    r_faci = simulate(depot, initial, vehicles, events, BUDGET_MS,
                      use_aco=True, aco_kwargs=ACO_KWARGS,
                      aco_rng=random.Random(SEED), use_fuzzy_budget=True)

    print("  Running ACO+Multi-Fuzzy...")
    r_mfz  = simulate(depot, initial, vehicles, events, BUDGET_MS,
                      use_aco=True, aco_kwargs=ACO_KWARGS,
                      aco_rng=random.Random(SEED), use_multi_fuzzy=True)

    print("  Running ACO+Threshold...")
    r_thr  = simulate(depot, initial, vehicles, events, BUDGET_MS,
                      use_aco=True, aco_kwargs=ACO_KWARGS,
                      aco_rng=random.Random(SEED), use_threshold_budget=True)

    print("  Running GA+Fuzzy...")
    r_ga   = simulate(depot, initial, vehicles, events, BUDGET_MS,
                      use_ga=True, ga_kwargs=GA_KWARGS, use_fuzzy_budget=True)

    print("  Running ACO+Repair (fixed budget)...")
    r_aco  = simulate(depot, initial, vehicles, events, BUDGET_MS,
                      use_aco=True, aco_kwargs=ACO_KWARGS,
                      aco_rng=random.Random(SEED), use_fuzzy_budget=False)

    print("  Running Full Re-opt...")
    r_reo  = simulate_full_reopt(depot, initial, vehicles, events)

    print("  Running Static...")
    r_sta  = simulate_static(depot, initial, vehicles, events)

    return {
        "FACI-DVRP (ACO+Fuzzy)": summarize(r_faci),
        "ACO+Multi-Fuzzy":        summarize(r_mfz),
        "ACO+Threshold":          summarize(r_thr),
        "GA+Fuzzy":               summarize(r_ga),
        "ACO+Repair (fixed)":     summarize(r_aco),
        "Full Re-opt":            summarize(r_reo),
        "Static":                 summarize(r_sta),
    }


# -----------------------------------------------------------------------
# Output helpers
# -----------------------------------------------------------------------

def save_csv(all_results, path):
    rows = []
    for (inst_name, _, label), method_results in zip(INSTANCES, all_results):
        for method, stats in method_results.items():
            rows.append({
                "instance": inst_name,
                "type": label,
                "method": method,
                **stats,
            })
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved: {path}")


def save_text_table(all_results, path):
    lines = []
    lines.append("=" * 80)
    lines.append("MULTI-INSTANCE RESULTS  (Solomon C101 / R101 / RC101, seed=42)")
    lines.append("=" * 80)

    header = f"{'Method':<28} {'Cost':>8} {'Avg ms':>8} {'Max ms':>8} {'Accept':>8} {'Stab':>7}"
    sep    = "-" * 70

    for (inst_name, _, label), method_results in zip(INSTANCES, all_results):
        lines.append(f"\n  {inst_name}  [{label}]")
        lines.append("  " + sep)
        lines.append("  " + header)
        lines.append("  " + sep)
        for method, s in method_results.items():
            marker = "  *" if "FACI" in method else "   "
            lines.append(
                f"{marker} {method:<25} "
                f"{s['final_cost']:>8} "
                f"{s['avg_latency']:>8} "
                f"{s['max_latency']:>8} "
                f"{s['acceptance']:>8} "
                f"{s['avg_stability']:>7}"
            )
        lines.append("  " + sep)

    lines.append("\n  * = proposed method (FACI-DVRP)")
    lines.append("=" * 80)
    text = "\n".join(lines)
    path.write_text(text)
    print(f"Saved: {path}")
    print("\n" + text)


def plot_bar(all_results, metric, ylabel, filename):
    inst_names = [i[0] for i in INSTANCES]
    x = np.arange(len(inst_names))
    width = 0.15
    methods = list(all_results[0].keys())
    colors  = ["#1a7a3c", "#2ca05a", "#265ead", "#d46a00", "#555555", "#aaaaaa", "#cccccc"]

    fig, ax = plt.subplots(figsize=(10, 4))
    for j, (method, color) in enumerate(zip(methods, colors)):
        vals = [res[method][metric] for res in all_results]
        bars = ax.bar(x + j * width, vals, width, label=method, color=color, alpha=0.85)

    ax.set_xlabel("Solomon Instance")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel} by Instance and Method")
    ax.set_xticks(x + width * 2)
    ax.set_xticklabels(inst_names)
    ax.legend(fontsize=8, loc="upper right")
    plt.tight_layout()
    plt.savefig(OUT_DIR / filename, dpi=150)
    plt.close()
    print(f"Saved: {OUT_DIR / filename}")


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    for inst in INSTANCES:
        results = run_instance(*inst)
        all_results.append(results)

    save_csv(all_results, OUT_DIR / "summary_table.csv")
    save_text_table(all_results, OUT_DIR / "summary_table.txt")
    plot_bar(all_results, "final_cost",   "Final Routing Cost",      "cost_by_instance.png")
    plot_bar(all_results, "avg_latency",  "Avg Update Latency (ms)", "latency_by_instance.png")
    plot_bar(all_results, "avg_stability","Avg Route Stability",     "stability_by_instance.png")


if __name__ == "__main__":
    main()
