"""
experiments/robustness_experiment.py

Robustness / sensitivity study for FACI-DVRP.
Tests whether results hold when key assumptions change.

Three studies:

B1 — Base budget sensitivity
  Vary base_budget_ms: 30, 50, 80 ms
  Shows the fuzzy controller degrades gracefully (proportionality preserved)
  Compares FACI-DVRP vs ACO+fixed at each budget level.

B2 — Event intensity
  Vary dynamic customer ratio: 10%, 20%, 30%, 40%, 50%
  Shows method handles heavier event loads without breaking.

B3 — Fuzzy membership boundary sensitivity
  Shift fuzzy MF peaks ±0.1 from their designed values
  Shows results are not fragile to exact MF tuning.

Usage:
    cd dvrp-ci-routing
    python experiments/robustness_experiment.py

Outputs (saved to experiments/results/robustness/):
    b1_budget_sensitivity.txt / .csv / .png
    b2_intensity.txt / .csv / .png
    b3_mf_sensitivity.txt / .csv / .png
"""

import csv
import random
from pathlib import Path

import matplotlib.pyplot as plt

from dvrp.data_loader import load_solomon_csv, make_fleet
from dvrp.simulator import simulate


# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------

INSTANCE_PATH = Path("solomon_dataset/C1/C101.csv")  # Use C101 for all robustness studies
SEED = 42
ACO_KWARGS = dict(n_ants=10, n_iterations=20, alpha=1.0, beta=2.0, rho=0.5)
OUT_DIR = Path("experiments/results/robustness")


# -----------------------------------------------------------------------
# Shared helpers
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
    costs = [m.total_cost for m in metrics]
    lats  = [m.update_ms  for m in metrics]
    stabs = [m.stability  for m in metrics]
    n = len(metrics)
    return {
        "final_cost":    round(costs[-1], 1),
        "avg_latency":   round(sum(lats) / n, 2),
        "avg_stability": round(sum(stabs) / n, 3),
        "acceptance":    sum(1 for m in metrics if m.accepted),
    }


def save_csv(rows, fieldnames, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {path}")


# -----------------------------------------------------------------------
# B1 — Base budget sensitivity
# -----------------------------------------------------------------------

def run_b1():
    print("\n" + "="*60)
    print("  B1: Base Budget Sensitivity (C101, dynamic=30%)")
    print("="*60)

    depot, all_customers = load_solomon_csv(INSTANCE_PATH)
    vehicles = make_fleet(INSTANCE_PATH)
    initial, dynamic = split_customers(all_customers, 0.30, SEED)
    events = build_event_stream(dynamic, all_customers, SEED)

    budgets = [20, 30, 50, 80, 100]
    rows = []

    for base_ms in budgets:
        r_fuzzy = simulate(depot, initial, vehicles, events, base_ms,
                           use_aco=True, aco_kwargs=ACO_KWARGS,
                           aco_rng=random.Random(SEED),
                           use_fuzzy_budget=True)
        r_fixed = simulate(depot, initial, vehicles, events, base_ms,
                           use_aco=True, aco_kwargs=ACO_KWARGS,
                           aco_rng=random.Random(SEED),
                           use_fuzzy_budget=False)
        sf = summarize(r_fuzzy)
        sx = summarize(r_fixed)
        rows.append({
            "base_ms": base_ms,
            "fuzzy_cost": sf["final_cost"],
            "fixed_cost": sx["final_cost"],
            "fuzzy_lat":  sf["avg_latency"],
            "fixed_lat":  sx["avg_latency"],
            "fuzzy_stab": sf["avg_stability"],
            "fixed_stab": sx["avg_stability"],
        })
        print(f"  base={base_ms:3d}ms  "
              f"fuzzy={sf['final_cost']:7.1f} ({sf['avg_latency']:.1f}ms)  "
              f"fixed={sx['final_cost']:7.1f} ({sx['avg_latency']:.1f}ms)")

    # Save
    save_csv(rows, list(rows[0].keys()), OUT_DIR / "b1_budget_sensitivity.csv")

    # Text table
    lines = ["="*65,
             "B1: BASE BUDGET SENSITIVITY  (C101, dynamic=30%, seed=42)",
             "="*65,
             f"{'Base':>6}  {'Fuzzy Cost':>10} {'Lat':>6}  {'Fixed Cost':>10} {'Lat':>6}  {'Δ Cost':>8}",
             "-"*65]
    for r in rows:
        delta = r["fuzzy_cost"] - r["fixed_cost"]
        sign = "+" if delta >= 0 else ""
        lines.append(
            f"  {r['base_ms']:>4}ms  "
            f"{r['fuzzy_cost']:>10.1f} {r['fuzzy_lat']:>5.1f}ms  "
            f"{r['fixed_cost']:>10.1f} {r['fixed_lat']:>5.1f}ms  "
            f"  {sign}{delta:.1f}"
        )
    lines.append("="*65)
    text = "\n".join(lines)
    (OUT_DIR / "b1_budget_sensitivity.txt").write_text(text)
    print("\n" + text)

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    bvals = [r["base_ms"] for r in rows]
    ax1.plot(bvals, [r["fuzzy_cost"] for r in rows], "o-", color="#1a7a3c", label="FACI-DVRP (Fuzzy)")
    ax1.plot(bvals, [r["fixed_cost"] for r in rows], "s--", color="#4472C4", label="ACO+Fixed")
    ax1.set_xlabel("Base Budget (ms)"); ax1.set_ylabel("Final Cost")
    ax1.set_title("B1: Cost vs Base Budget"); ax1.legend(); ax1.grid(alpha=0.3)

    ax2.plot(bvals, [r["fuzzy_lat"] for r in rows], "o-", color="#1a7a3c", label="FACI-DVRP (Fuzzy)")
    ax2.plot(bvals, [r["fixed_lat"] for r in rows], "s--", color="#4472C4", label="ACO+Fixed")
    ax2.set_xlabel("Base Budget (ms)"); ax2.set_ylabel("Avg Latency (ms)")
    ax2.set_title("B1: Latency vs Base Budget"); ax2.legend(); ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUT_DIR / "b1_budget_sensitivity.png", dpi=150)
    plt.close()
    print(f"Saved: {OUT_DIR / 'b1_budget_sensitivity.png'}")

    return rows


# -----------------------------------------------------------------------
# B2 — Event intensity
# -----------------------------------------------------------------------

def run_b2():
    print("\n" + "="*60)
    print("  B2: Event Intensity — Dynamic Ratio (C101, base=50ms)")
    print("="*60)

    depot, all_customers = load_solomon_csv(INSTANCE_PATH)
    vehicles = make_fleet(INSTANCE_PATH)

    ratios = [0.10, 0.20, 0.30, 0.40, 0.50]
    rows = []

    for ratio in ratios:
        initial, dynamic = split_customers(all_customers, ratio, SEED)
        events = build_event_stream(dynamic, all_customers, SEED)
        n_dyn = len(dynamic)

        r_fuzzy = simulate(depot, initial, vehicles, events, 50,
                           use_aco=True, aco_kwargs=ACO_KWARGS,
                           aco_rng=random.Random(SEED),
                           use_fuzzy_budget=True)
        r_fixed = simulate(depot, initial, vehicles, events, 50,
                           use_aco=True, aco_kwargs=ACO_KWARGS,
                           aco_rng=random.Random(SEED),
                           use_fuzzy_budget=False)
        sf = summarize(r_fuzzy)
        sx = summarize(r_fixed)
        rows.append({
            "dynamic_ratio": ratio,
            "n_dynamic": n_dyn,
            "n_events": len(events),
            "fuzzy_cost": sf["final_cost"],
            "fixed_cost": sx["final_cost"],
            "fuzzy_stab": sf["avg_stability"],
            "fixed_stab": sx["avg_stability"],
            "fuzzy_accept": sf["acceptance"],
            "fixed_accept": sx["acceptance"],
        })
        print(f"  ratio={ratio:.0%} ({n_dyn} dyn, {len(events)} events)  "
              f"fuzzy={sf['final_cost']:7.1f} stab={sf['avg_stability']:.3f}  "
              f"fixed={sx['final_cost']:7.1f} stab={sx['avg_stability']:.3f}")

    save_csv(rows, list(rows[0].keys()), OUT_DIR / "b2_intensity.csv")

    lines = ["="*70,
             "B2: EVENT INTENSITY ROBUSTNESS  (C101, base=50ms, seed=42)",
             "="*70,
             f"{'Ratio':>7} {'N dyn':>6}  "
             f"{'Fuzzy Cost':>10} {'Stab':>6}  "
             f"{'Fixed Cost':>10} {'Stab':>6}  {'Δ':>6}",
             "-"*70]
    for r in rows:
        delta = r["fuzzy_cost"] - r["fixed_cost"]
        sign = "+" if delta >= 0 else ""
        lines.append(
            f"  {r['dynamic_ratio']:>5.0%}  {r['n_dynamic']:>5}  "
            f"  {r['fuzzy_cost']:>10.1f} {r['fuzzy_stab']:>6.3f}  "
            f"  {r['fixed_cost']:>10.1f} {r['fixed_stab']:>6.3f}  "
            f"  {sign}{delta:.1f}"
        )
    lines.append("="*70)
    text = "\n".join(lines)
    (OUT_DIR / "b2_intensity.txt").write_text(text)
    print("\n" + text)

    # Plot
    fig, ax = plt.subplots(figsize=(8, 4))
    pct = [r["dynamic_ratio"] * 100 for r in rows]
    ax.plot(pct, [r["fuzzy_cost"] for r in rows], "o-", color="#1a7a3c", label="FACI-DVRP (Fuzzy)")
    ax.plot(pct, [r["fixed_cost"] for r in rows], "s--", color="#4472C4", label="ACO+Fixed")
    ax.set_xlabel("Dynamic Customer Ratio (%)"); ax.set_ylabel("Final Cost")
    ax.set_title("B2: Cost vs Event Intensity (C101)"); ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "b2_intensity.png", dpi=150)
    plt.close()
    print(f"Saved: {OUT_DIR / 'b2_intensity.png'}")

    return rows


# -----------------------------------------------------------------------
# B3 — Fuzzy MF boundary sensitivity
# -----------------------------------------------------------------------

def run_b3():
    print("\n" + "="*60)
    print("  B3: Fuzzy MF Boundary Sensitivity (C101, dynamic=30%)")
    print("="*60)

    import dvrp.fuzzy_budget as fb_module

    depot, all_customers = load_solomon_csv(INSTANCE_PATH)
    vehicles = make_fleet(INSTANCE_PATH)
    initial, dynamic = split_customers(all_customers, 0.30, SEED)
    events = build_event_stream(dynamic, all_customers, SEED)

    # Default MF: LOW=trimf(0.0,0.0,0.5), MED=trimf(0.2,0.5,0.8), HIGH=trimf(0.5,1.0,1.0)
    # We shift the LOW-MED boundary (0.5) and HIGH-MED boundary (0.5) by ±0.1
    # Concretely: shift the overlap points (c of LOW / a of HIGH) by ±0.1

    # Save originals
    orig_low  = (0.0, 0.0, 0.5)
    orig_med  = (0.2, 0.5, 0.8)
    orig_high = (0.5, 1.0, 1.0)

    shifts = [-0.1, -0.05, 0.0, 0.05, 0.1]
    rows = []

    for shift in shifts:
        # Shifted MF boundaries
        low_c  = max(0.1, orig_low[2]  + shift)   # c of LOW
        high_a = min(0.9, orig_high[0] + shift)   # a of HIGH
        med_a  = max(0.0, orig_med[0]  + shift)
        med_c  = min(1.0, orig_med[2]  + shift)

        # Monkey-patch the MF functions for this run
        def make_low(c): return lambda s: fb_module._trimf(s, 0.0, 0.0, c)
        def make_med(a, c): return lambda s: fb_module._trimf(s, a, 0.5+shift, c)
        def make_high(a): return lambda s: fb_module._trimf(s, a, 1.0, 1.0)

        fb_module._sev_low    = make_low(low_c)
        fb_module._sev_medium = make_med(med_a, med_c)
        fb_module._sev_high   = make_high(high_a)

        r_fuzzy = simulate(depot, initial, vehicles, events, 50,
                           use_aco=True, aco_kwargs=ACO_KWARGS,
                           aco_rng=random.Random(SEED),
                           use_fuzzy_budget=True)
        sf = summarize(r_fuzzy)
        rows.append({
            "shift": shift,
            "low_c": round(low_c, 2),
            "high_a": round(high_a, 2),
            "cost": sf["final_cost"],
            "avg_latency": sf["avg_latency"],
            "stability": sf["avg_stability"],
        })
        marker = " ← default" if shift == 0.0 else ""
        print(f"  shift={shift:+.2f}  low_c={low_c:.2f} high_a={high_a:.2f}  "
              f"cost={sf['final_cost']:.1f}  lat={sf['avg_latency']:.2f}ms{marker}")

    # Restore originals
    fb_module._sev_low    = lambda s: fb_module._trimf(s, 0.0, 0.0, 0.5)
    fb_module._sev_medium = lambda s: fb_module._trimf(s, 0.2, 0.5, 0.8)
    fb_module._sev_high   = lambda s: fb_module._trimf(s, 0.5, 1.0, 1.0)

    save_csv(rows, list(rows[0].keys()), OUT_DIR / "b3_mf_sensitivity.csv")

    lines = ["="*65,
             "B3: FUZZY MF BOUNDARY SENSITIVITY  (C101, dynamic=30%, seed=42)",
             "="*65,
             f"{'Shift':>7} {'LOW_c':>6} {'HIGH_a':>7}  {'Cost':>8} {'Lat':>6} {'Stab':>6}",
             "-"*65]
    for r in rows:
        marker = " ← default" if r["shift"] == 0.0 else ""
        lines.append(
            f"  {r['shift']:>+5.2f}  {r['low_c']:>5.2f}  {r['high_a']:>6.2f}  "
            f"  {r['cost']:>8.1f} {r['avg_latency']:>5.2f}ms "
            f"{r['stability']:>6.3f}{marker}"
        )
    lines.append("="*65)
    text = "\n".join(lines)
    (OUT_DIR / "b3_mf_sensitivity.txt").write_text(text)
    print("\n" + text)

    # Plot
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot([r["shift"] for r in rows], [r["cost"] for r in rows],
            "o-", color="#1a7a3c", linewidth=2)
    ax.axvline(0, color="gray", linestyle="--", alpha=0.5, label="Default MFs")
    default_cost = next(r["cost"] for r in rows if r["shift"] == 0.0)
    ax.axhline(default_cost, color="gray", linestyle=":", alpha=0.5)
    ax.set_xlabel("MF Boundary Shift"); ax.set_ylabel("Final Cost (C101)")
    ax.set_title("B3: Cost Sensitivity to Fuzzy MF Boundaries")
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "b3_mf_sensitivity.png", dpi=150)
    plt.close()
    print(f"Saved: {OUT_DIR / 'b3_mf_sensitivity.png'}")

    return rows


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    b1 = run_b1()
    b2 = run_b2()
    b3 = run_b3()

    print("\n" + "="*60)
    print("  All robustness studies complete.")
    print("  Results saved to: experiments/results/robustness/")
    print("="*60)


if __name__ == "__main__":
    main()
