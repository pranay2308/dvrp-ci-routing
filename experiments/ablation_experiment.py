"""
experiments/ablation_experiment.py

Ablation study: isolates the contribution of each FACI-DVRP component.

Four configurations, same ACO constructor, same event stream:

  Config 1 — ACO only (Static)
    No dynamic event handling. Routes are built once and never updated.
    Shows the baseline quality of ACO initial construction.

  Config 2 — ACO + Insertion (fixed 50ms, no 2-opt)
    Handles new_customer events via insertion only. Traffic/weather events
    are accepted but no route repair is run. Uses fixed budget.
    Shows value of insertion repair alone (no local search, no fuzzy).

  Config 3 — ACO + Fuzzy budget (insertion only, no 2-opt)
    Same as Config 2 but budget is fuzzy-adaptive.
    Isolates the fuzzy budget contribution from local search quality.

  Config 4 — ACO + Fuzzy + Full Repair (FACI-DVRP)
    Full proposed method: fuzzy budget + insertion + 2-opt + relocate.
    Shows the combined contribution.

The gap between Config 2 and Config 3 measures fuzzy-budget-alone value.
The gap between Config 3 and Config 4 measures local search value.
The gap between Config 1 and Config 2 measures insertion repair value.

Usage:
    cd dvrp-ci-routing
    python experiments/ablation_experiment.py

Outputs (saved to experiments/results/ablation/):
    ablation_table.txt   — formatted table ready for paper
    ablation_table.csv   — raw data
    ablation_cost.png    — bar chart
"""

import csv
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from dvrp.baseline import simulate_static
from dvrp.data_loader import load_solomon_csv, make_fleet
from dvrp.simulator import simulate


# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------

INSTANCES = [
    ("C101",  Path("solomon_dataset/C1/C101.csv"),   "Clustered"),
    ("R101",  Path("solomon_dataset/R1/R101.csv"),   "Random"),
    ("RC101", Path("solomon_dataset/RC1/RC101.csv"), "Mixed"),
]

DYNAMIC_CUSTOMER_RATIO = 0.30
BUDGET_MS = 50
SEED = 42
ACO_KWARGS = dict(n_ants=10, n_iterations=20, alpha=1.0, beta=2.0, rho=0.5)

OUT_DIR = Path("experiments/results/ablation")

CONFIGS = [
    "ACO only (static)",
    "ACO + Insertion (fixed, no 2-opt)",
    "ACO + Fuzzy + Insertion (no 2-opt)",
    "ACO + Fuzzy + Repair (FACI-DVRP)",
]


# -----------------------------------------------------------------------
# Helpers
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
        "acceptance":    f"{accepted}/{n}",
        "avg_stability": round(sum(stabs) / n, 3),
    }


# -----------------------------------------------------------------------
# Run one instance
# -----------------------------------------------------------------------

def run_instance(name, path, label):
    print(f"\n{'='*60}")
    print(f"  Ablation — Instance: {name}  ({label})")
    print(f"{'='*60}")

    depot, all_customers = load_solomon_csv(path)
    vehicles = make_fleet(path)
    initial, dynamic = split_customers(all_customers, DYNAMIC_CUSTOMER_RATIO, SEED)
    events = build_event_stream(dynamic, all_customers, SEED)

    print(f"  {len(initial)} initial + {len(dynamic)} dynamic + 2 disruptions = {len(events)} events")

    # All four configs receive random.Random(SEED) as the ACO RNG so they
    # all start from an identical ACO-built solution — this is what a valid
    # ablation requires. Using an isolated RNG (not global random.seed) also
    # makes Config 4 match the main multi-instance experiment, which likewise
    # passes random.Random(SEED) to each ACO call.

    # Config 1 — Static baseline (NN constructor, no event handling)
    print("  [1/4] Static (NN, no updates)...")
    r_static = simulate_static(depot, initial, vehicles, events)

    # Config 2 — ACO + Insertion, fixed budget, no 2-opt
    print("  [2/4] ACO + Insertion (fixed, no 2-opt)...")
    r_insert = simulate(
        depot, initial, vehicles, events, BUDGET_MS,
        use_aco=True, aco_kwargs=ACO_KWARGS,
        aco_rng=random.Random(SEED),
        use_fuzzy_budget=False,
        use_local_search=False,
    )

    # Config 3 — ACO + Fuzzy budget + Insertion only, no 2-opt
    print("  [3/4] ACO + Fuzzy + Insertion (no 2-opt)...")
    r_fuzzy_only = simulate(
        depot, initial, vehicles, events, BUDGET_MS,
        use_aco=True, aco_kwargs=ACO_KWARGS,
        aco_rng=random.Random(SEED),
        use_fuzzy_budget=True,
        use_local_search=False,
    )

    # Config 4 — Full FACI-DVRP
    print("  [4/4] ACO + Fuzzy + Repair (FACI-DVRP)...")
    r_faci = simulate(
        depot, initial, vehicles, events, BUDGET_MS,
        use_aco=True, aco_kwargs=ACO_KWARGS,
        aco_rng=random.Random(SEED),
        use_fuzzy_budget=True,
        use_local_search=True,
    )

    results = {
        "ACO only (static)":               summarize(r_static),
        "ACO + Insertion (fixed, no 2-opt)": summarize(r_insert),
        "ACO + Fuzzy + Insertion (no 2-opt)": summarize(r_fuzzy_only),
        "ACO + Fuzzy + Repair (FACI-DVRP)": summarize(r_faci),
    }

    print(f"\n  Results for {name}:")
    for cfg, s in results.items():
        marker = "* " if "FACI" in cfg else "  "
        print(f"  {marker}{cfg:<40} cost={s['final_cost']:>8}  "
              f"lat={s['avg_latency']:>5}ms  stab={s['avg_stability']}")

    return results


# -----------------------------------------------------------------------
# Output helpers
# -----------------------------------------------------------------------

def save_csv(all_results, path):
    rows = []
    for (inst_name, _, label), method_results in zip(INSTANCES, all_results):
        for method, stats in method_results.items():
            rows.append({"instance": inst_name, "type": label, "method": method, **stats})
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved: {path}")


def save_text_table(all_results, path):
    lines = []
    lines.append("=" * 82)
    lines.append("ABLATION STUDY  —  Solomon C101 / R101 / RC101  (seed=42, ACO constructor)")
    lines.append("=" * 82)
    lines.append("Component contributions:")
    lines.append("  Config 1→2: value of insertion repair")
    lines.append("  Config 2→3: value of fuzzy budget (same repair, adaptive ceiling)")
    lines.append("  Config 3→4: value of 2-opt local search + cross-route relocate")
    lines.append("")

    header = f"  {'Config':<42} {'Cost':>8} {'Avg ms':>7} {'Accept':>8} {'Stab':>7}"
    sep    = "  " + "-" * 76

    for (inst_name, _, label), method_results in zip(INSTANCES, all_results):
        lines.append(f"\n  {inst_name}  [{label}]")
        lines.append(sep)
        lines.append(header)
        lines.append(sep)
        configs = list(method_results.items())
        for i, (method, s) in enumerate(configs):
            marker = "* " if "FACI" in method else f"{i+1} "
            lines.append(
                f"  {marker}{method:<40} "
                f"{s['final_cost']:>8} "
                f"{s['avg_latency']:>7} "
                f"{s['acceptance']:>8} "
                f"{s['avg_stability']:>7}"
            )
            # Print delta vs previous config
            if i > 0:
                prev_cost = configs[i-1][1]['final_cost']
                delta = s['final_cost'] - prev_cost
                sign = "+" if delta >= 0 else ""
                lines.append(f"    {'':40} Δcost vs prev: {sign}{delta:.1f}")
        lines.append(sep)

    lines.append("\n  * = proposed method (FACI-DVRP)")
    lines.append("=" * 82)
    text = "\n".join(lines)
    path.write_text(text)
    print(f"Saved: {path}")
    print("\n" + text)


def plot_ablation(all_results):
    inst_names = [i[0] for i in INSTANCES]
    configs = CONFIGS
    colors = ["#aaaaaa", "#4472C4", "#ED7D31", "#1a7a3c"]
    x = np.arange(len(inst_names))
    width = 0.18

    fig, ax = plt.subplots(figsize=(11, 5))
    for j, (cfg, color) in enumerate(zip(configs, colors)):
        vals = [res[cfg]["final_cost"] for res in all_results]
        bars = ax.bar(x + j * width, vals, width, label=cfg, color=color, alpha=0.88)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15,
                    f"{val:.0f}", ha="center", va="bottom", fontsize=7.5, rotation=0)

    ax.set_xlabel("Solomon Instance", fontsize=12)
    ax.set_ylabel("Final Routing Cost (lower is better)", fontsize=12)
    ax.set_title("Ablation Study: Component-wise Contribution to FACI-DVRP Cost",
                 fontsize=13, fontweight="bold")
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(inst_names, fontsize=11)
    ax.legend(fontsize=9, loc="upper right")
    ax.set_ylim(0, max(
        res[cfg]["final_cost"]
        for res in all_results for cfg in configs
    ) * 1.15)
    plt.tight_layout()
    out = OUT_DIR / "ablation_cost.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved: {out}")


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    for inst in INSTANCES:
        results = run_instance(*inst)
        all_results.append(results)

    save_csv(all_results, OUT_DIR / "ablation_table.csv")
    save_text_table(all_results, OUT_DIR / "ablation_table.txt")
    plot_ablation(all_results)


if __name__ == "__main__":
    main()
