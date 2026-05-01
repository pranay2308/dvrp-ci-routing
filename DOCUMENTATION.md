# Technical Documentation

## FACI-DVRP: Fuzzy-Adaptive CI Framework for Dynamic Vehicle Routing

**Authors:** Pranay Kukkadapu — Georgia State University, MSc Data Science and Analytics
           Sai Ruchitha Parambil Mundath — Georgia State University, MSc Computer Science

---

## Table of Contents

1. [Problem Formulation](#1-problem-formulation)
2. [System Architecture](#2-system-architecture)
3. [Algorithm: ACO Initial Construction](#3-algorithm-aco-initial-construction)
4. [Algorithm: Fuzzy Time Budget Controller](#4-algorithm-fuzzy-time-budget-controller)
5. [Algorithm: Genetic Algorithm Constructor](#5-algorithm-genetic-algorithm-constructor)
6. [Algorithm: 2-opt Local Search](#6-algorithm-2-opt-local-search)
7. [Dynamic Event Types](#7-dynamic-event-types)
8. [Baselines](#8-baselines)
9. [Evaluation Metrics](#9-evaluation-metrics)
10. [Multi-Instance Results](#10-multi-instance-results)
11. [Module Reference](#11-module-reference)

---

## 1. Problem Formulation

### Vehicle Routing Problem (VRP)

Given:
- A depot node `d` at coordinates `(x_d, y_d)`
- A set of customers `C = {c_1, ..., c_n}`, each with coordinates and a demand `q_i`
- A fleet of vehicles `V = {v_1, ..., v_k}`, each with capacity `Q`

Find: An assignment of customers to vehicles and a visitation sequence per vehicle such that:
- Each customer is visited exactly once
- Each vehicle's total demand does not exceed capacity `Q`
- Total travel distance is minimized

### Dynamic Extension (DVRP)

In the dynamic setting, the customer set and network conditions change over time:

| Event | Description |
|---|---|
| `new_customer` | A new order arrives and must be inserted into the current plan |
| `traffic_delay` | Travel time on a specific road segment increases by a factor `f ≥ 1` |
| `weather_disruption` | A global speed reduction applies to all segments (factor `w ≥ 1`) |

The system must respond to each event within a **strict time budget** whose duration is determined by the fuzzy controller (default base: 50ms).

---

## 2. System Architecture

The FACI-DVRP pipeline runs in two phases: an offline construction phase before any events arrive, and an online repair phase that handles each event as it occurs.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Simulation Loop                                │
│                                                                       │
│   Initial Customers (70% of Solomon instance)                         │
│          │                                                            │
│          ▼                                                            │
│   ┌─────────────────────────────────────┐                            │
│   │   CI Constructor (choose one)       │                            │
│   │                                     │                            │
│   │   ACO  — pheromone-guided           │──────────►  Solution₀      │
│   │   GA   — OX crossover + tournament  │                  │         │
│   └─────────────────────────────────────┘                  │         │
│                                                             │         │
│   ┌─────────────────────────────────────┐                  │         │
│   │         Event Stream (30%)          │                  │         │
│   │  [new_customer, traffic_delay, ...]  │                  │         │
│   └─────────────────────────────────────┘                  │         │
│                    │                                        │         │
│                    ▼                               ◄────────┘         │
│   ┌────────────────────────────────┐                                  │
│   │  Fuzzy Time Budget Controller  │                                  │
│   │                                │                                  │
│   │  event → severity score        │                                  │
│   │  severity → fuzzy membership   │──────► budget_ms                │
│   │  rules → defuzzified budget    │                                  │
│   └────────────────────────────────┘                                  │
│                    │                                                  │
│                    ▼                                                  │
│   ┌─────────────────────────────────────────────────────┐            │
│   │   2-opt Repair (within budget_ms)                    │            │
│   │                                                      │            │
│   │   new_customer       → best-position insert + 2-opt  │            │
│   │   traffic_delay      → 2-opt on affected routes      │            │
│   │   weather_disruption → 2-opt on all routes           │            │
│   └─────────────────────────────────────────────────────┘            │
│                    │                                                  │
│                    ▼                                                  │
│              Solutionₜ  →  Record metrics (cost, latency, stability) │
└──────────────────────────────────────────────────────────────────────┘
```

The three CI techniques are:
- **CI #1 — ACO:** Offline initial route construction via pheromone-guided search
- **CI #2 — Fuzzy Logic:** Online latency management via event severity classification
- **CI #3 — 2-opt (evolutionary-style local search):** Online route repair within the allocated budget

A **Genetic Algorithm (GA)** constructor is available as an alternative to ACO for CI #1 and is used in the GA+Fuzzy experimental configuration.

---

## 3. Algorithm: ACO Initial Construction

Ant Colony Optimization builds the initial routing plan before any dynamic events occur. This is the offline phase; quality matters more than speed here.

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `n_ants` | 10 | Number of ants per iteration |
| `n_iterations` | 20 | Number of ACO iterations |
| `alpha` | 1.0 | Pheromone trail exponent |
| `beta` | 2.0 | Heuristic (1/distance) exponent |
| `rho` | 0.5 | Pheromone evaporation rate |
| `tau_0` | 1.0 | Initial pheromone value on all edges |

### Pseudocode

```
Initialize pheromone: tau[i][j] = tau_0 for all node pairs (i, j)
Initialize heuristic: eta[i][j] = 1 / dist(i, j)

For each iteration:
    For each ant:
        Build solution:
            For each vehicle:
                current = depot
                While unassigned customers exist:
                    feasible = customers where cumulative demand <= capacity
                    For each feasible customer c:
                        weight[c] = tau[current][c]^alpha * eta[current][c]^beta
                    Select next proportional to weight (roulette wheel)
                    Assign selected customer to current vehicle's route
        Evaluate solution cost
        Track global best

    Evaporate: tau[i][j] *= (1 - rho)  for all edges
    Deposit:   tau[i][j] += 1/cost     on edges of iteration-best solution

Return global best solution
```

### Note on Empty Routes

All vehicles are included in the output solution, even those with no assigned customers. This ensures that when dynamic new_customer events arrive during simulation, unused vehicles are available for insertion — a necessary design choice for maintaining 100% acceptance rate.

---

## 4. Algorithm: Fuzzy Time Budget Controller

### Purpose

The fuzzy controller manages **event-handling latency**, not route cost. It replaces a flat fixed budget (e.g., always 50ms) with an event-adaptive budget that allocates less compute time to low-severity events and more to high-severity ones. This reduces average latency without sacrificing acceptance rate.

**Design goal:** Implement a stability-preserving, policy-driven event-response strategy where computational resources scale proportionally to disruption impact. The fuzzy controller allocates ~35ms ceiling for low-severity events and up to 80ms for severe weather — a principled, continuously-varying alternative to fixed budgets and hand-coded thresholds. At n=100, actual repair completes in 2–4ms; the budget ceiling bounds worst-case allocation and becomes the binding constraint at larger scales.

### Input: Event Severity Scoring

Each incoming event is mapped to a scalar severity score in [0, 1] before entering the fuzzy system:

| Event Type | Severity Formula | Notes |
|---|---|---|
| `new_customer` | `severity = 0.25` | Fixed low score; single insertion is always low impact |
| `traffic_delay` | `severity = min(1.0, (factor - 1.0) / 2.0)` | factor=1.5 → 0.25; factor=3.0 → 1.0 |
| `weather_disruption` | `severity = min(1.0, (factor - 1.0) / 0.5)` | factor=1.3 → 0.60; steeper scaling than traffic |

### Membership Functions

The fuzzy input universe is severity ∈ [0, 1]. Three triangular membership functions partition this space:

| Linguistic Term | Function | Parameters (a, b, c) | Peak |
|---|---|---|---|
| `LOW` | trimf | (0.0, 0.0, 0.5) | 0.0 |
| `MEDIUM` | trimf | (0.2, 0.5, 0.8) | 0.5 |
| `HIGH` | trimf | (0.5, 1.0, 1.0) | 1.0 |

Triangular membership function definition:
```
trimf(x; a, b, c) = max(0, min( (x-a)/(b-a), (c-x)/(c-b) ))
```

The LOW set is left-shoulder shaped (a=b=0), meaning severity=0 gives full membership in LOW. The HIGH set is right-shoulder shaped (b=c=1).

### Fuzzy Rules

| Rule | Antecedent | Consequent | Crisp centroid |
|---|---|---|---|
| R1 | IF severity is LOW    | THEN budget is TIGHT    | 30 ms |
| R2 | IF severity is MEDIUM | THEN budget is NORMAL   | 50 ms |
| R3 | IF severity is HIGH   | THEN budget is EXTENDED | 80 ms |

Output fuzzy sets (TIGHT, NORMAL, EXTENDED) are singletons at their crisp centroid values.

### Defuzzification

The output budget is computed as a weighted average of the crisp centroids, scaled to the configured `base_budget_ms`:

```
mu_low    = trimf(severity, 0.0, 0.0, 0.5)
mu_medium = trimf(severity, 0.2, 0.5, 0.8)
mu_high   = trimf(severity, 0.5, 1.0, 1.0)

numerator   = mu_low * 30 + mu_medium * 50 + mu_high * 80
denominator = mu_low + mu_medium + mu_high

budget_raw = numerator / denominator          # in [30, 80] ms for base=50
budget_ms  = budget_raw * (base_budget_ms / 50.0)   # scale to configured base
```

### Example Outputs (base_budget_ms=50)

| Event | Severity | mu_low | mu_med | mu_high | Budget |
|---|---|---|---|---|---|
| new_customer | 0.25 | 0.50 | 0.17 | 0.00 | ~35 ms |
| traffic_delay (factor=2.0) | 0.65 | 0.00 | 0.50 | 0.30 | ~61 ms |
| weather_disruption (factor=1.3) | 0.80 | 0.00 | 0.00 | 0.60 | ~80 ms |
| weather_disruption (factor=1.5) | 1.00 | 0.00 | 0.00 | 1.00 | ~80 ms |

### Experimental Results

| Instance | Fixed Budget Avg Latency | Fuzzy Budget Avg Latency | Reduction |
|---|---|---|---|
| C101 (Clustered) | 47.9 ms | 33.7 ms | 29.6% |
| R101 (Random)    | 48.1 ms | 34.1 ms | 29.1% |
| RC101 (Mixed)    | 48.2 ms | 33.9 ms | 29.7% |

---

## 5. Algorithm: Genetic Algorithm Constructor

The GA constructor is an alternative to ACO for the offline initial construction phase. It uses a giant-tour representation with order-crossover and provides a direct CI-vs-CI comparison against ACO when both are paired with the fuzzy budget controller.

### Encoding

A chromosome is a **giant-tour permutation** — a single ordered list of all customer IDs. The chromosome does not encode vehicle assignments directly; those are determined at decode time.

### Decoding: Greedy Capacity Split

```
Given a permutation [c_1, c_2, ..., c_n]:

route = []
current_load = 0
For each customer c_i in permutation:
    If current_load + demand(c_i) <= vehicle_capacity:
        route.append(c_i)
        current_load += demand(c_i)
    Else:
        Assign route to next available vehicle
        route = [c_i]
        current_load = demand(c_i)
Assign final route to next available vehicle
```

This decode is deterministic given a permutation, making fitness evaluation straightforward.

### Genetic Operators

**Crossover — Order Crossover (OX):**
```
Given parents P1 = [a, b, c, d, e, f] and P2 = [d, b, e, a, f, c]:
1. Select a random segment from P1, e.g., positions [2,4]: [_, _, c, d, e, _]
2. Copy segment to offspring at same positions
3. Fill remaining positions left-to-right with P2's order, skipping already-placed genes
Result offspring: [b, a, c, d, e, f]
```

OX preserves relative ordering of customers not in the segment, which tends to maintain good sub-sequences from both parents.

**Mutation — Swap Mutation:**
```
Select two random positions i, j in the permutation
Swap chromosome[i] and chromosome[j]
```

Applied with probability `mutation_rate` per individual per generation.

**Selection — Binary Tournament:**
```
Select k=2 individuals at random from the population
Return the individual with lower fitness (lower cost)
```

Tournament selection applies selection pressure without requiring global population sorting.

**Elitism — Top-1:**
```
Preserve the single best individual from generation t into generation t+1 unchanged
```

Guarantees that the best solution found is never lost.

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `pop_size` | 30 | Population size |
| `n_generations` | 50 | Number of generations |
| `mutation_rate` | 0.15 | Per-individual mutation probability |
| `tournament_k` | 2 | Binary tournament size |

### Pseudocode

```
Initialize: generate pop_size random permutations of all customers
Evaluate: compute fitness (total route cost after greedy decode) for each individual

For generation in [1, n_generations]:
    elite = individual with minimum fitness
    new_population = [elite]    # elitism: carry best forward

    While len(new_population) < pop_size:
        parent1 = tournament_select(population)
        parent2 = tournament_select(population)
        child   = ox_crossover(parent1, parent2)
        If random() < mutation_rate:
            child = swap_mutate(child)
        new_population.append(child)

    population = new_population
    Evaluate all individuals

Return decode(best individual in final population)
```

### Experimental Finding

ACO+Fuzzy (FACI-DVRP) outperforms GA+Fuzzy on total route cost across all three Solomon instance types tested:

| Instance | ACO+Fuzzy Cost | GA+Fuzzy Cost | ACO Advantage |
|---|---|---|---|
| C101 (Clustered) | 1988 | 2426 | −18% |
| R101 (Random)    | 1698 | 2167 | −22% |
| RC101 (Mixed)    | 2135 | 2635 | −19% |

ACO's advantage is consistent across all three instance types. The pheromone matrix accumulates 200 construction passes (10 ants × 20 iterations), efficiently encoding spatial proximity knowledge that the GA's greedy-split decoder with swap mutation cannot replicate in the same number of evaluations. The GA's greedy capacity-split decoder assigns customers in permutation order, which may not align with geographic clusters, limiting the effectiveness of OX crossover for VRPTW instances.

---

## 6. Algorithm: 2-opt Local Search

Applied after insertion for `new_customer` events, and as the primary repair strategy for `traffic_delay` and `weather_disruption` events.

### Best-Improvement 2-opt

```
For a single route with customers [c_1, ..., c_n]:

Repeat until no improvement:
    best_improvement = 0
    For i in [0, n-2]:
        For k in [i+2, n]:
            candidate = reverse segment [i+1, k] in route
            delta = cost(candidate) - cost(current)
            If delta < best_improvement:
                best_improvement = delta
                best_move = (i, k)

    If best_move found:
        Apply reversal, update route

Return improved route
```

The function accepts an optional `dist_fn` parameter. When responding to disruption events, the delay/weather-aware distance function is passed, ensuring that 2-opt improvements are computed under the actual current network conditions rather than base Euclidean distances.

**Time complexity:** O(n^2) per pass, where n = customers in the route. Multiple passes until convergence.

---

## 7. Dynamic Event Types

### 7.1 new_customer

```python
event = {
    "type": "new_customer",
    "customer": Customer(id=31, x=45.2, y=67.8, demand=10)
}
```

**Response:**
1. Find best-position insertion across all routes (minimizes additional travel distance, subject to capacity), using the current delay/weather-aware dist_fn
2. All steps run within `budget_ms` determined by the fuzzy controller

If no feasible insertion position exists within budget, the event is rejected (counted in acceptance metrics).

---

### 7.2 traffic_delay

```python
event = {
    "type": "traffic_delay",
    "segment": (5, 12),   # customer IDs of the delayed edge
    "factor": 2.0          # travel time on this edge doubles
}
```

**Response:**
1. Update `delay_map[(5, 12)] = 2.0` and `delay_map[(12, 5)] = 2.0` (bidirectional)
2. Identify all routes containing customer 5 or customer 12
3. Run 2-opt on those routes using the delay-aware distance function
4. Re-evaluate total solution cost with updated `delay_map`

The delay is **persistent** — it remains active for all subsequent events and future cost evaluations.

---

### 7.3 weather_disruption

```python
event = {
    "type": "weather_disruption",
    "factor": 1.3    # all travel 30% slower
}
```

**Response:**
1. Update `weather_factor = 1.3`
2. Run 2-opt on all non-empty routes using `make_dist_fn(delay_map, 1.3)`
3. Re-evaluate total solution cost with global slowdown applied

The weather factor is **persistent** and **compounds** with any active traffic delays: a segment with a 2x traffic delay under 1.3x weather incurs 2.6x its base distance cost.

---

## 8. Baselines

### 8.1 Static Baseline

- Builds initial solution once using nearest-neighbor constructor
- Never modifies routes for any event (all events ignored)
- Costs are re-evaluated under active delays/weather so cost degradation from unhandled disruptions is visible
- Acceptance rate: 0% (no events processed)
- Route stability: 1.000 (routes never change)
- Represents the **do-nothing** lower bound on implementation effort

### 8.2 Full Re-optimization Baseline

- On every event (including disruptions): rebuild the entire solution from scratch using nearest-neighbor
- No time budget — runs to completion regardless of wall-clock time
- Tracks actual computation time for fair latency comparison
- Represents **maximum achievable quality** at the cost of route stability and predictable latency
- Stability is below 1.000 because rebuilding from scratch can reassign customers to different vehicles: C101=0.900, R101=0.856, RC101=0.809

---

## 9. Evaluation Metrics

| Metric | Description | Computed in |
|---|---|---|
| **Total routing cost** | Sum of all route distances using current dist_fn | `total_solution_cost()` |
| **Update latency (ms)** | Wall-clock time to process each event | `simulator.py` |
| **Acceptance rate** | Fraction of events successfully handled | `SimMetrics.accepted` |
| **Route stability** | Fraction of customers on the same route after update | `route_stability()` |

### Stability Formula

```
stability = |{c : route(c, old) == route(c, new)}| / |common customers|
```

A value of 1.000 means no customer changed vehicles during any update.
A value of 0.900 means 10% of customers were reassigned to different vehicles across all events.

### Acceptance Rate

For repair-based methods (ACO+Fuzzy, GA+Fuzzy, ACO+fixed), acceptance is 100% across all instances tested. Events are rejected only if no feasible insertion exists within the budget — this did not occur on the 32-event sequences tested.

---

## 10. Multi-Instance Results

Results across three Solomon benchmark instances (100 customers each, 32 dynamic events, seed=42). Instances represent the three spatial distribution classes in the Solomon benchmark.

### Cost and Latency Summary

| Method | C101 Cost | C101 Lat | R101 Cost | R101 Lat | RC101 Cost | RC101 Lat | Stability |
|---|---|---|---|---|---|---|---|
| FACI-DVRP (ACO+Fuzzy+Repair)  | 1988.4 | 2.5 ms | 1697.5 | 3.6 ms | 2135.2 | 3.7 ms | 0.988 |
| ACO+Multi-Fuzzy (3-input FIS) | 1988.4 | 2.5 ms | 1697.5 | 3.5 ms | 2135.2 | 3.7 ms | 0.988 |
| ACO+Threshold Budget          | 1988.4 | 2.7 ms | 1697.5 | 3.6 ms | 2135.2 | 3.7 ms | 0.988 |
| GA+Fuzzy+Repair               | 2426.1 | 2.6 ms | 2167.2 | 2.9 ms | 2635.1 | 2.7 ms | 0.988 |
| ACO+Repair (fixed 50ms)       | 1988.4 | 2.5 ms | 1697.5 | 3.8 ms | 2135.2 | 3.9 ms | 0.988 |
| Full Re-opt (NN rebuild)      | 1666.1 | 3.4 ms | 1526.7 | 3.4 ms | 1802.4 | 3.5 ms | 0.900/0.856/0.809 |
| Static (no updates)           | 1156.0 | 0.0 ms | 1085.0 | 0.0 ms | 1328.6 | 0.0 ms | 1.000 |

All repair-based methods: 100% acceptance rate. Static: 0% acceptance (events ignored; serves only ~70 initial customers).

### Interpretation

1. **Fuzzy controller proportions budget to event severity.** Actual repair work completes in 2–4 ms per event at n=100. The fuzzy controller allocates ~35 ms ceiling for simple new_customer events and up to 80 ms for severe weather disruptions. Its value is proportional resource allocation — not a guaranteed cost reduction. No single budget policy (fuzzy, threshold, or fixed) dominates cost across all instances.

2. **ACO outperforms GA on solution cost across all instances.** ACO+Fuzzy achieves 18% lower cost than GA+Fuzzy on C101 (1988 vs. 2426), 22% on R101 (1698 vs. 2167), and 19% on RC101 (2135 vs. 2635). ACO's pheromone-guided construction consistently builds better initial solutions than the GA's greedy-split decoder for Solomon VRPTW instances.

3. **All ACO budget variants achieve identical cost.** ACO+fixed, ACO+Threshold, FACI-DVRP, and ACO+Multi-Fuzzy all achieve 1988.4 / 1697.5 / 2135.2 on C101/R101/RC101. Budget policy determines time allocation per event, not final routing cost. At n=100, all repair completes within any budget tier (actual work: 2–4 ms). The fuzzy controller's value is interpretability and proportional allocation, not cost reduction.

---

## 11. Module Reference

### `src/dvrp/models.py`

Core domain classes:
- `Customer(id, x, y, demand)` — customer node
- `Vehicle(id, capacity)` — vehicle with capacity constraint
- `Route(vehicle, customers)` — ordered customer sequence for one vehicle
- `Solution(routes)` — complete assignment of customers to vehicles

### `src/dvrp/cost.py`

- `euclidean(a, b)` — base Euclidean distance between two nodes
- `make_dist_fn(delay_map, weather_factor)` — factory returning a distance function that applies active delays and weather multiplier
- `route_distance(depot, customers, dist_fn)` — total cost of one route (depot → c_1 → ... → c_n → depot)
- `is_capacity_feasible(customers, capacity)` — returns True if total demand fits within capacity

### `src/dvrp/aco.py`

- `aco_constructor(depot, customers, vehicles, n_ants, n_iterations, alpha, beta, rho, tau_0)` — ACO initial solution builder; returns `Solution`

### `src/dvrp/fuzzy_budget.py`

- `fuzzy_time_budget(event, base_budget_ms)` — main entry point; maps an event dict to a budget in milliseconds
- `explain_budget(event, base_budget_ms)` — returns human-readable string showing severity score, membership values, and computed budget (useful for debugging and verification)
- `_severity_score(event)` — internal; maps event dict to scalar severity in [0, 1]
- `_membership(severity)` — internal; returns (mu_low, mu_medium, mu_high) tuple

### `src/dvrp/ga_constructor.py`

- `ga_constructor(depot, customers, vehicles, pop_size, n_generations, mutation_rate)` — GA initial solution builder; returns `Solution`
- `_ox_crossover(p1, p2)` — order crossover on two permutations
- `_swap_mutate(perm)` — swap mutation on a permutation
- `_tournament_select(population, fitnesses, k)` — binary tournament selection
- `_decode(depot, permutation, vehicles)` — greedy capacity-split decoder; maps permutation to `Solution`

### `src/dvrp/constructors.py`

- `nearest_neighbor_constructor(depot, customers, vehicles)` — greedy NN baseline builder; used by Full Re-opt baseline

### `src/dvrp/dynamic.py`

- `insert_customer_best_position(depot, solution, new_customer)` — finds and applies best-cost feasible insertion position across all routes

### `src/dvrp/local_search.py`

- `two_opt_best_improvement(depot, customers, dist_fn)` — best-improvement 2-opt for a single route; returns improved customer list

### `src/dvrp/repair.py`

- `repair_with_time_budget(depot, solution, new_customer, budget_ms, dist_fn)` — time-bounded best-position insertion within `budget_ms`; returns repaired solution or None if no feasible position found

### `src/dvrp/time_budget.py`

- `run_with_time_budget(budget_ms, step_fn, accept_fn)` — generic real-time executor; runs `step_fn` repeatedly until `budget_ms` elapsed, returns best accepted result

### `src/dvrp/simulator.py`

- `simulate(depot, customers, vehicles, events, budget_ms, use_aco, use_ga, use_fuzzy_budget, aco_kwargs, ga_kwargs)` — main simulation entry point
- `SimMetrics` — per-event result dataclass: `(event_type, cost, latency_ms, accepted, stability)`
- `route_stability(old_solution, new_solution)` — computes fraction of customers on same vehicle
- `total_solution_cost(depot, solution, dist_fn)` — evaluates total route cost under current disruption state

### `src/dvrp/baseline.py`

- `simulate_static(depot, customers, vehicles, events)` — no-update baseline
- `simulate_full_reopt(depot, customers, vehicles, events)` — full nearest-neighbor rebuild baseline

### `src/dvrp/data_loader.py`

- `load_solomon_csv(path)` — parses Solomon benchmark CSV, returns `(depot, customers)` tuple
- `make_fleet(instance_path, n_vehicles, capacity)` — builds vehicle fleet with Solomon-standard defaults (25 vehicles × capacity 200 for C1/R1/RC1)

### `experiments/benchmark_experiment.py`

Single-instance experiment runner. Loads C101 (configurable via `INSTANCE_PATH`), runs all five methods, saves per-event CSV and comparison plots to `experiments/results/`.

### `experiments/multi_instance_experiment.py`

Multi-instance experiment runner. Iterates over C101, R101, and RC101. Saves per-instance CSVs and an aggregated summary table to `experiments/results/multi/summary_table.txt`.
