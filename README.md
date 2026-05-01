# FACI-DVRP: Fuzzy-Adaptive CI Framework for Dynamic Vehicle Routing

**Pranay Kukkadapu** — Masters in Data Science and Analytics, Georgia State University
**Sai Ruchitha Parambil Mundath** — Masters in Computer Science, Georgia State University

> CSc 8810 Computational Intelligence · Dr. Yanqing Zhang · Spring 2026
> Submission deadline: May 2, 2026

---

## What This Project Does

Real-world delivery routes break constantly — new customers call in, roads get congested, weather slows everything down. Classical re-optimization is too slow for real-time use. This project builds **FACI-DVRP**, a framework that handles disruptions using three Computational Intelligence techniques working in a pipeline. The core novelty is a **Fuzzy Logic time budget controller** that proportions computational budget to event severity. The project also provides an empirical CI-vs-CI comparison between ACO and GA constructors under the fuzzy budget regime.

---

## The Contributions

### 1. Fuzzy-Based Adaptive Repair-Budget Allocation

A Mamdani fuzzy inference system implements a **stability-preserving, policy-driven event-response strategy**: low-severity events (e.g., a single new customer) receive a tight budget ceiling (~35ms); high-severity events (e.g., severe weather) receive an extended ceiling (~80ms). This is a principled, continuously-varying alternative to fixed budgets and hand-coded thresholds — computational resources scale proportionally to disruption impact, with interpretable fuzzy rules that make the allocation policy transparent and tunable.

An extended **3-input Mamdani FIS** (ACO+Multi-Fuzzy) also incorporates `affected_route_ratio` and `route_load_factor` from the current solution state, assigning tighter budgets when few routes are affected and extending them for heavily loaded fleets under severe disruptions. At n=100, the 3-input FIS produces identical final costs to the single-input FIS (budget is non-binding), but provides richer allocation semantics that would benefit larger-scale instances where budget ceilings are binding.

### 2. Empirical Finding: ACO Outperforms GA on Cost Under Fuzzy Budget

When using the fuzzy budget controller, ACO's pheromone-guided construction produces lower-cost solutions than the GA (OX crossover + greedy capacity split) across all three benchmark instances. On C101, ACO+Fuzzy achieves **1988 vs. GA+Fuzzy's 2426 — an 18% lower cost**. This finding holds on R101 (1698 vs. 2167, −22%) and RC101 (2135 vs. 2635, −19%) as well. The GA's greedy-split decoder with swap mutation does not explore the VRPTW solution space as effectively as ACO's pheromone-reinforced probabilistic construction for these instances.

---

## Three CI Techniques

```
BEFORE THE DAY                   WHEN DISRUPTION HITS        FIX IT (FAST)
─────────────────────────────────────────────────────────────────────────────
┌─────────────────┐   event!   ┌──────────────────┐   budget  ┌───────────┐
│  Ant Colony     │ ─────────► │   Fuzzy Logic    │ ────────► │  2-opt    │
│  Optimization   │            │   Controller     │           │ + Repair  │
│  (ACO)          │            │                  │           │           │
│                 │            │  new_customer    │           │ Only fix  │
│  Pheromone-     │            │  → ~30ms budget  │           │ affected  │
│  guided route   │            │  traffic delay   │           │ routes.   │
│  construction   │            │  → ~50ms budget  │           │ Warm      │
│  before any     │            │  weather disrupt │           │ start     │
│  events arrive  │            │  → ~80ms budget  │           │ reuse.    │
└─────────────────┘            └──────────────────┘           └───────────┘

  CI Technique 1                 CI Technique 2              CI Technique 3
```

A **Genetic Algorithm (GA)** constructor is also implemented as a drop-in replacement for ACO in the initial construction phase, enabling a direct CI-vs-CI cost comparison.

---

## Multi-Instance Results

Results across three Solomon benchmark instances (100 customers each, 32 dynamic events, seed=42). Cost = total route distance; Avg Latency = mean wall-clock ms per event.

| Method | C101 Cost | C101 Latency | R101 Cost | R101 Latency | RC101 Cost | RC101 Latency |
|---|---|---|---|---|---|---|
| FACI-DVRP (ACO+Fuzzy+Repair)  | **1988.4** | 2.5 ms | **1697.5** | 3.6 ms | **2135.2** | 3.7 ms |
| ACO+Multi-Fuzzy (3-input FIS) | 1988.4 | 2.5 ms | 1697.5 | 3.5 ms | 2135.2 | 3.7 ms |
| ACO+Threshold Budget          | 1988.4 | 2.7 ms | 1697.5 | 3.6 ms | 2135.2 | 3.7 ms |
| GA+Fuzzy+Repair               | 2426.1 | 2.6 ms | 2167.2 | 2.9 ms | 2635.1 | 2.7 ms |
| ACO+Repair (fixed 50ms)       | 1988.4 | 2.5 ms | 1697.5 | 3.8 ms | 2135.2 | 3.9 ms |
| Full Re-opt (NN rebuild)      | 1666.1 | 3.4 ms | 1526.7 | 3.4 ms | 1802.4 | 3.5 ms |
| Static (no updates)           | 1156.0 | 0.0 ms | 1085.0 | 0.0 ms | 1328.6 | 0.0 ms |

All repair-based methods: 100% acceptance rate, 0.988 route stability.
Full Re-opt stability: C101=0.900, R101=0.856, RC101=0.809.
Static: 0% acceptance (events ignored), cost reflects only the initial 70-customer plan.

---

## Key Findings

- **Local search is the sole cost-reducing component.** The ablation study shows that adding fuzzy budget allocation to insertion-only repair produces Δ=0 cost change on all three instances. Adding 2-opt local search + cross-route relocate reduces cost by 7–14%. The fuzzy controller is a resource allocation policy, not a cost optimizer.

- **All ACO budget variants achieve identical cost.** ACO+fixed, ACO+Threshold, FACI-DVRP (ACO+Fuzzy), and ACO+Multi-Fuzzy all achieve 1988.4 / 1697.5 / 2135.2 on C101 / R101 / RC101. Budget policy determines how repair time is allocated per event, not how much cost improvement is achieved. This confirms the budget ceiling is non-binding at n=100 (actual work completes in 2–4ms within any budget tier).

- **ACO+Fuzzy outperforms GA+Fuzzy on cost by 18–22% across all instances.** ACO's pheromone-guided construction produces better initial solutions than the GA's greedy-split decoder for Solomon VRPTW instances. Cost gap: 18% on C101 (1988 vs 2426), 22% on R101 (1698 vs 2167), 19% on RC101 (2135 vs 2635). Both CI constructors work within the same fuzzy+repair framework; ACO simply builds better starting routes.

- **Fuzzy controller correctly proportions budget to event severity.** The fuzzy controller assigns ~30ms to low-severity events (single new customer) and up to ~80ms to high-severity disruptions (severe weather). Actual repair work completes in 2–4ms; the budget bounds the worst-case ceiling, not average latency.

- **Static cost is lower but misleading.** Static only serves the initial 70 customers — it never inserts the 30 dynamic arrivals. All repair-based methods serve all 100 customers at higher total distance, which is the correct real-world behavior.

---

## Project Structure

```
dvrp-ci-routing/
├── src/dvrp/
│   ├── models.py          # Customer, Vehicle, Route, Solution
│   ├── cost.py            # Euclidean distance, delay-aware dist_fn
│   ├── constructors.py    # Nearest-neighbor constructor
│   ├── aco.py             # Ant Colony Optimization constructor  [CI #1]
│   ├── fuzzy_budget.py    # Fuzzy logic adaptive time budget     [CI #2]
│   ├── ga_constructor.py  # Genetic Algorithm constructor        [CI #3]
│   ├── dynamic.py         # Best-position customer insertion
│   ├── local_search.py    # 2-opt best-improvement
│   ├── repair.py          # Time-budgeted repair pipeline
│   ├── time_budget.py     # Generic real-time execution framework
│   ├── simulator.py       # Main DVRP simulator (all event types)
│   ├── baseline.py        # Static + full re-opt baselines
│   └── data_loader.py     # Solomon CSV parser
├── experiments/
│   ├── benchmark_experiment.py       # Single instance experiment (C101)
│   └── multi_instance_experiment.py  # All 3 instances (C101, R101, RC101)
├── experiments/results/
│   ├── benchmark_metrics.csv         # Per-event data, single instance
│   └── multi/
│       └── summary_table.txt         # Aggregated multi-instance results
├── solomon_dataset/
│   ├── C1/   (C101–C109)   ← clustered
│   ├── R1/   (R101–R112)   ← random
│   └── RC1/                ← mixed
├── tests/                  # Unit tests (pytest)
├── IEEE_PAPER.md           # Full IEEE-format research paper
├── create_slides.py        # Generates presentation.pptx (12 slides)
├── presentation.pptx       # PowerPoint slides
└── DOCUMENTATION.md        # Full technical documentation
```

---

## How to Run

```bash
# Install dependencies
pip install -e .

# Single instance benchmark (C101, 5 methods)
python experiments/benchmark_experiment.py

# All three instances (C101, R101, RC101)
python experiments/multi_instance_experiment.py

# Run unit tests
python -m pytest tests/
```

---

## Where to Find the Numbers

| Output | Location |
|---|---|
| Per-event latency and cost (single instance) | Terminal output from `benchmark_experiment.py` |
| Per-event CSV data | `experiments/results/benchmark_metrics.csv` |
| Multi-instance summary table | `experiments/results/multi/summary_table.txt` |
| Aggregated averages in this README | Computed from the CSV; see "Multi-Instance Results" above |

---

## References

1. M. Dorigo and L. M. Gambardella, "Ant colony system: A cooperative learning approach to the traveling salesman problem," *IEEE Transactions on Evolutionary Computation*, vol. 1, no. 1, pp. 53–66, 1997.
2. J. H. Holland, *Adaptation in Natural and Artificial Systems*. Ann Arbor: University of Michigan Press, 1975.
3. M. M. Solomon, "Algorithms for the vehicle routing and scheduling problems with time window constraints," *Operations Research*, vol. 35, no. 2, pp. 254–265, 1987.
4. V. Pillac, M. Gendreau, C. Guéret, and A. L. Medaglia, "A review of dynamic vehicle routing problems," *European Journal of Operational Research*, vol. 225, no. 1, pp. 1–11, 2013.
5. L. A. Zadeh, "Fuzzy sets," *Information and Control*, vol. 8, no. 3, pp. 338–353, 1965.
6. H. N. Psaraftis, "Dynamic vehicle routing problems," in *Vehicle Routing: Methods and Studies*, B. L. Golden and A. A. Assad, Eds. Amsterdam: North-Holland, 1988, pp. 223–248.
7. D. Goldberg, *Genetic Algorithms in Search, Optimization, and Machine Learning*. Reading, MA: Addison-Wesley, 1989.
8. G. B. Dantzig and J. H. Ramser, "The truck dispatching problem," *Management Science*, vol. 6, no. 1, pp. 80–91, 1959.
9. S. Ichoua, M. Gendreau, and J.-Y. Potvin, "Exploiting knowledge about future demands for real-time vehicle dispatching," *Transportation Science*, vol. 40, no. 2, pp. 211–225, 2006.
10. C. D. Tarantilis and C. T. Kiranoudis, "A meta-heuristic algorithm for the efficient distribution of perishable foods," *Journal of Food Engineering*, vol. 50, no. 1, pp. 1–9, 2001.
