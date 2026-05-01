# FACI-DVRP: Fuzzy-Adaptive Ant Colony Optimization with Genetic Algorithm Comparison for Dynamic Vehicle Routing Under Real-Time Constraints

**Pranay Kukkadapu**
Masters in Data Science and Analytics
Georgia State University
Atlanta, Georgia, USA

**Sai Ruchitha Parambil Mundath**
Masters in Computer Science
Georgia State University
Atlanta, Georgia, USA

*CSc 8810 Computational Intelligence — Spring 2026*

---

## Abstract

Dynamic Vehicle Routing Problems (DVRP) require continuous online re-planning as new customers arrive, road delays occur, and weather disrupts travel speeds. Real-time dispatch systems impose strict latency requirements that make full re-optimization impractical. This paper presents FACI-DVRP (Fuzzy-Adaptive Computational Intelligence for DVRP), a three-component framework combining Ant Colony Optimization (ACO) for initial route construction, a Mamdani-style fuzzy logic controller for per-event time budget management, and 2-opt local search with cross-route relocation for incremental repair. A Genetic Algorithm (GA) constructor using Order Crossover is developed and evaluated alongside ACO under identical dynamic conditions. An extended 3-input Mamdani FIS incorporating affected_route_ratio and route_load_factor is also developed and evaluated. Three findings emerge from multi-instance experiments on Solomon benchmarks C101, R101, and RC101. First, the ablation study establishes that local search (2-opt + cross-route relocate) is the sole cost-reducing component: adding fuzzy budget allocation to insertion-only repair produces zero cost improvement (Δ = 0.0 on all three instances), confirming that the fuzzy controller is a resource allocation policy, not a cost optimizer. Second, all ACO-based budget variants — fixed, threshold, single-input fuzzy (FACI-DVRP), and 3-input fuzzy — produce identical final routing costs when starting from the same initial ACO solution (1988, 1698, 2135 on C101/R101/RC101 respectively), demonstrating that budget policy determines how repair time is allocated, not how much improvement is achieved. Third, ACO+Fuzzy consistently outperforms GA+Fuzzy on solution cost by 18–22% across all instances (C101: 1988 vs. 2426; R101: 1698 vs. 2167; RC101: 2135 vs. 2635), confirming that ACO's pheromone-guided construction produces substantially better initial solutions than GA's greedy-split decoder for Solomon VRPTW benchmarks. All repair methods achieve 100% event acceptance and 0.988 average route stability, validating incremental repair as the dominant strategy for real-time DVRP.

---

## I. Introduction

### A. Motivation

The Vehicle Routing Problem (VRP) is one of the most studied combinatorial optimization problems in operations research, with direct applications in courier delivery, emergency logistics, food distribution, and ride-hailing fleet management. Classical VRP formulations assume that all problem parameters — customer locations, demands, and road network costs — are fully known before routes are planned. In practice, this assumption rarely holds. A delivery fleet dispatched at 8 a.m. will encounter new customer orders throughout the morning, unexpected road closures from accidents, and weather events that slow all vehicles simultaneously.

The Dynamic VRP (DVRP) models this operational reality. In the DVRP, the problem instance evolves continuously during execution: new customers must be inserted into active routes, delay events force cost re-evaluations, and disruptions may render existing routes infeasible. The fundamental challenge is that each event triggers a re-planning cycle that must complete within a strict time budget — typically tens of milliseconds for real-time dispatch — or the vehicle has already passed the decision point [1].

This latency constraint forces a fundamental tradeoff: full re-optimization from scratch produces the best possible solution but is too slow; ignoring events degrades service quality; incremental repair falls in between and is the dominant practical strategy. Yet most DVRP frameworks allocate a fixed time budget to every event regardless of complexity — treating a severe weather disruption affecting all routes identically to a single low-demand customer insertion. This is computationally wasteful for simple events and potentially insufficient for complex ones. What is needed is a policy-driven event-response strategy that allocates repair resources proportionally to disruption impact, preserving route stability while adapting to event severity.

Computational Intelligence (CI) offers a natural language for modeling this tradeoff. Fuzzy logic, in particular, provides an interpretable, rule-based mechanism for mapping event characteristics to resource allocations without hard-coded thresholds [5]. Ant Colony Optimization (ACO) and Genetic Algorithms (GA) provide high-quality construction heuristics that prime the incremental repair with a strong initial solution.

### B. Contributions

This paper makes two primary contributions, stated precisely so that the experimental results can be evaluated against them honestly:

**Contribution 1: Fuzzy-Based Adaptive Repair-Budget Allocation for Real-Time DVRP.**
A Mamdani-style fuzzy inference system maps disruption severity to per-event repair time budgets using three triangular membership functions and three rules. This introduces a stability-preserving, policy-driven event-response strategy: tight budgets (~35 ms) for low-severity insertions, normal budgets (50 ms) for moderate disruptions, and extended budgets (up to 80 ms) for severe weather events affecting all routes. The fuzzy formulation provides a principled, continuously-varying alternative to fixed budgets and hand-coded severity thresholds, with interpretable rules that make the allocation policy transparent and adjustable. Ablation confirms that this allocation policy does not alter final routing cost (Δ=0 without local search), but proportional allocation correctly concentrates repair time on high-impact events.

**Contribution 2: Empirical CI Constructor Comparison — ACO Outperforms GA on Solution Cost.**
An empirical finding from the multi-instance evaluation is that ACO+Fuzzy consistently produces lower-cost dynamic solutions than GA+Fuzzy across all three benchmark instances. The cost gap is 18% on C101 (1988 vs. 2426), 22% on R101 (1698 vs. 2167), and 19% on RC101 (2135 vs. 2635). ACO's pheromone-guided probabilistic construction builds better initial solutions than the GA's greedy capacity-split decoder with OX crossover for Solomon VRPTW instances. Importantly, neither the fuzzy budget controller nor local search eliminates this gap — the constructor quality advantage persists throughout the simulation. This suggests that pheromone-based spatial memory is more effective than recombination-based exploration for geographically structured routing benchmarks.

### C. Paper Structure

Section II reviews related work on DVRP, ACO, GA, and fuzzy logic in routing. Section III describes the FACI-DVRP framework architecture and problem formulation. Section IV details the fuzzy logic time budget controller design and provides worked numerical examples. Section V describes the GA constructor. Section VI presents the full multi-instance experimental evaluation with honest discussion of results. Section VII concludes with limitations and future work directions.

---

## II. Related Work

### A. Dynamic Vehicle Routing

The DVRP was first formally characterized by Psaraftis [1], who distinguished between online problems (where decisions must be made before the full information is revealed) and re-optimization problems (where routes can be updated each time new information arrives). The key operational modes he identified — immediate insertion, periodic re-optimization, and rolling horizon — remain the dominant strategies today.

Pillac et al. [4] provide the most comprehensive modern taxonomy of DVRP, categorizing variants by information structure (deterministic vs. stochastic arrivals), decision horizon (immediate vs. delayed response), and objective (minimizing total cost vs. minimizing maximum lateness). Their survey establishes that incremental repair dominates full re-optimization for systems with sub-second response requirements, a finding directly relevant to the design of FACI-DVRP. Gendreau and Potvin [3] earlier surveyed dynamic dispatching approaches, noting that the stability of solutions — the degree to which vehicle assignments remain consistent across events — is as important as cost in real-world deployments, because drivers and customers are disrupted by frequent reassignments.

A recurring finding in DVRP literature is that full re-optimization on every event is computationally impractical beyond small instances. Even fast nearest-neighbor heuristics, when applied from scratch on each event, produce unacceptably high latency and low route stability. This motivates the incremental repair approach central to FACI-DVRP.

### B. Ant Colony Optimization for VRP

Ant Colony Optimization was introduced by Dorigo and Gambardella [5] through the Ant Colony System (ACS), which models the indirect communication of ant colonies via pheromone trails. In the ACS, ants probabilistically construct solutions guided by pheromone intensity (learned from past good solutions) and heuristic information (typically inverse distance). After all ants have constructed solutions, global pheromone update deposits additional pheromone on the best tour found in proportion to its quality, reinforcing good arcs.

Montemanni et al. [6] extended ACS to the dynamic VRP by maintaining a persistent pheromone matrix that is updated incrementally as new customers arrive. When a new customer appears, additional pheromone deposition around the new customer's neighborhood guides ants toward profitable insertions in subsequent construction phases. This incremental pheromone update strategy is conceptually related to the ACO constructor in FACI-DVRP, though FACI-DVRP uses ACO only for the initial offline construction and relies on 2-opt repair rather than re-running the full ant colony for each event.

ACO has shown strong empirical performance on clustered VRP instances (Solomon C-class) where the pheromone matrix efficiently captures spatial proximity patterns. Performance on random instances (R-class) is more variable, as pheromone trails may reinforce locally good but globally suboptimal routes.

### C. Genetic Algorithms for VRP

Holland's Genetic Algorithm [7] introduced the core operators — selection, crossover, and mutation — that underpin all modern evolutionary computation. For VRP, the standard encoding is a permutation chromosome (giant-tour) decoded into vehicle routes by a split procedure. The Order Crossover (OX) operator, used in this paper, was introduced specifically for permutation problems: it copies a sub-segment from one parent and fills remaining positions with elements from the second parent in their original relative order, preserving meaningful partial route structures.

GA applications to DVRP have generally used one of two strategies: periodic re-optimization (running the GA every k events, trading solution quality for responsiveness) or event-triggered restarts (running the GA to completion on severe events only). Neither approach natively supports variable time budgets or smooth adaptation to event severity. The GA in FACI-DVRP is used exclusively for initial construction, with the fuzzy controller and 2-opt repair handling all online event processing.

### D. Fuzzy Logic in Routing and Scheduling

Zadeh [10] introduced fuzzy sets as a formalism for reasoning with imprecise or gradual concepts, enabling rule-based systems that interpolate smoothly between categories rather than applying hard thresholds. In routing and scheduling, fuzzy logic has been applied primarily to handle uncertain demand [8] and soft time window constraints, where customer satisfaction degrades gradually rather than dropping to zero at a hard deadline.

Liong and Wan [8] applied fuzzy membership functions to model uncertain travel times in the Traveling Salesman Problem, demonstrating that fuzzy-augmented route selection outperforms deterministic approaches when travel time variability is high. However, the use of fuzzy logic specifically for computational resource allocation — deciding how much repair time to spend on each DVRP event based on its disruption severity — does not appear in the prior literature. The closest analogy is in real-time operating systems, where fuzzy logic has been used to allocate processor time to tasks of varying urgency [10]. FACI-DVRP transfers this concept directly to the DVRP domain: disruption severity maps to urgency, and repair time budget maps to processor time allocation.

This is the conceptual gap that FACI-DVRP fills. Prior DVRP frameworks either use a fixed time budget for all events or rely on hand-coded thresholds (e.g., "if event type is weather, use 80 ms; otherwise use 50 ms"). The fuzzy controller provides a principled, interpretable, continuously-varying alternative.

---

## III. FACI-DVRP Framework

### A. Problem Formulation

Let G = (V, E) be a complete undirected graph where V = {0, 1, ..., n}, with node 0 representing the depot and nodes 1 through n representing customers. Each customer i has a demand d_i > 0. A homogeneous fleet of K vehicles, each with capacity Q, originates and terminates at the depot. The static Capacitated VRP (CVRP) seeks a set of K routes R = {r_1, ..., r_K} minimizing the total Euclidean travel distance subject to the capacity constraint:

```
sum_{i in r_k} d_i <= Q,  for all k = 1,...,K
```

In the DVRP extension used here, the customer set C = {1, ..., n} is partitioned into an initial set C_0 (known at planning time, |C_0| = 0.7n) and a dynamic set C_dyn (arriving at random times during execution, |C_dyn| = 0.3n). Three event types can occur during execution:

- **new_customer**: A previously unknown customer arrives and must be inserted into an active route while respecting capacity.
- **traffic_delay**: A specific road segment (a, b) experiences a delay; the travel cost on that segment is multiplied by a factor f >= 1.0.
- **weather_disruption**: A global weather event multiplies all travel costs by a factor f >= 1.0.

The DVRP objective is to minimize total routing cost over the complete event horizon (serving all n customers, including dynamic arrivals) while satisfying the latency constraint: each event must be processed and a valid updated solution must be produced within the per-event time budget allocated by the fuzzy controller.

Route stability between consecutive solutions S_t and S_{t+1} is measured as the fraction of customers whose vehicle assignment does not change:

```
stability(S_t, S_{t+1}) = |{i in C : vehicle(i, S_t) = vehicle(i, S_{t+1})}| / |C|
```

Event acceptance rate is the fraction of events for which a valid (capacity-feasible) updated solution is produced within the time budget.

### B. Three-Phase Framework Architecture

FACI-DVRP separates computation into an offline construction phase executed once at planning time and an online event-processing phase executed for every arriving event.

**Phase 1 — Offline Initial Construction:**
Given the initial customer set C_0, the fleet specification (K, Q), and the distance matrix, build an initial solution S_0 using either the ACO constructor (primary FACI-DVRP method) or the GA constructor (comparison method). This phase runs without time constraints, allowing the constructor to produce the best possible starting solution.

**Phase 2 — Online Event Processing (executed per event):**
For each arriving event e at simulation time t:

1. **Compute disruption severity**: Apply the event-type-specific severity formula (Section IV-B) to produce s in [0, 1].
2. **Fuzzy budget computation**: Pass s through the Mamdani FIS to obtain effective_budget_ms.
3. **Apply event to world state**: Update the delay map (for traffic events) or global weather factor.
4. **Incremental repair**: Run the appropriate repair procedure (insertion for new customers, 2-opt for delay/weather events) within effective_budget_ms milliseconds.
5. **Record metrics**: Log final cost, update latency, stability against the previous solution, and acceptance status.

The key design principle is that Phase 1 sets the baseline quality and Phase 2 maintains it incrementally. The fuzzy controller in Step 2 ensures that the time budget in Step 4 is proportional to the complexity of each event, avoiding both wasted computation on trivial events and insufficient computation on severe disruptions.

### C. ACO Initial Constructor

The ACO constructor implements the Ant Colony System (ACS) with the following procedure: a colony of n_ants ants each construct a complete solution over n_iterations iterations. At each step, the current ant at node i selects the next node j according to a pseudo-random-proportional rule: with probability q_0 (exploitation parameter), the ant selects the node with the highest combined pheromone-heuristic score; otherwise, it samples from the pheromone-weighted distribution. The heuristic information is the inverse Euclidean distance: eta(i, j) = 1 / d(i, j).

After all ants complete their tours, global pheromone update is applied: pheromone on all arcs evaporates by factor (1 - rho), and the best-iteration tour deposits an additional 1 / cost_best on each of its arcs. Capacity constraints are enforced by starting a new route whenever the cumulative demand would exceed Q.

The ACO solution S_0 = ACO(C_0, K, Q) is used as-is for the online phase. The quality of S_0 directly impacts the final cost, as the 2-opt repair can only improve within the time budget — it cannot compensate for a poor initial solution over many low-severity events.

### D. 2-Opt Incremental Repair

The 2-opt repair procedure operates within the time deadline allocated by the fuzzy controller. For **new_customer events**, the procedure evaluates all feasible insertion positions across all K routes and inserts the new customer at the position minimizing the increase in total cost, subject to capacity feasibility. If multiple positions tie, the one with the smallest route load is chosen to preserve capacity slack.

For **traffic_delay and weather_disruption events**, the procedure runs 2-opt best-improvement on the affected routes (all routes for weather; routes using the delayed segment for traffic). The 2-opt operator considers all pairs of edges (i, i+1) and (j, j+1) within a route and reverses the sub-tour from i+1 to j if this reduces the route cost. The procedure iterates until no improving swap exists or the time deadline expires.

Routes with fewer than 4 customers are skipped (no 2-opt move is possible). The time check is performed at the start of each candidate pair evaluation, ensuring that the deadline is respected to within the evaluation granularity.

---

## IV. Fuzzy Logic Time Budget Controller

### A. Motivation: Why Fixed Budgets Fail

A naive DVRP system assigns a fixed time budget B_fixed to every event regardless of type or severity. Consider the consequences on the mixed-event stream used in this paper:

- A **new_customer** event with low demand requires only a single best-position insertion scan — O(K * n) comparisons — which typically completes in 5–15 ms. Allocating 50 ms to this event wastes 35–45 ms.
- A **weather_disruption** event with factor 1.3 invalidates the cost estimate of every arc in every route simultaneously. Effective re-optimization requires 2-opt to converge on multiple routes, which may require 60–80 ms with the instance sizes studied. Allocating only 50 ms cuts off the repair prematurely.

Over a stream of 32 events where most are low-severity new_customer arrivals, a fixed 50 ms budget incurs substantial unnecessary latency. The fuzzy controller addresses this directly: low-severity events receive tight budgets (around 30 ms), medium-severity events receive the nominal budget (50 ms), and high-severity events receive extended budgets (up to 80 ms). Averaged across the event stream, this reduces mean latency while maintaining or improving repair quality on the events that matter most.

### B. Input Variable: Disruption Severity

The fuzzy system uses a single input variable, disruption_severity s in [0, 1]. Severity is computed deterministically from the event dictionary using the following domain-knowledge formulas:

**new_customer events:**
```
s = 0.25   (constant)
```
New customer arrivals always have low severity because insertion requires O(Kn) work regardless of the customer's demand. The constant value of 0.25 places the event firmly in the LOW membership region.

**traffic_delay events:**
```
s = min(0.30 + 0.35 * (factor - 1.0),  1.0)
```
A delay factor of 1.0 (no change) gives s = 0.30 (low-medium). A factor of 2.0 (double travel time on the segment) gives s = 0.65 (medium-high). A factor of 3.0 gives s = 1.0 (fully high). The linear scaling reflects that repair complexity grows proportionally with the magnitude of the delay.

**weather_disruption events:**
```
s = min(0.50 + 0.50 * (factor - 1.0) / 0.5,  1.0)
```
Weather events start at severity 0.50 (medium) even for small factors, because they affect all routes simultaneously. A factor of 1.3 (30% global slowdown, as used in the experiments) gives s = 0.80 (high). A factor of 1.5 gives s = 1.0 (fully high). The steeper scaling relative to traffic delays reflects the wider scope of weather disruptions.

### C. Membership Functions

Three triangular membership functions partition the severity universe [0, 1]:

```
mu_LOW(s)    = trimf(s;  a=0.0, b=0.0, c=0.5)
mu_MEDIUM(s) = trimf(s;  a=0.2, b=0.5, c=0.8)
mu_HIGH(s)   = trimf(s;  a=0.5, b=1.0, c=1.0)
```

The triangular membership function is defined as:

```
         0              if x <= a  or  x >= c
trimf =  (x-a)/(b-a)   if  a < x <= b
         (c-x)/(c-b)   if  b < x <  c
```

The three functions overlap in the ranges [0.2, 0.5] and [0.5, 0.8], creating smooth interpolation zones. The midpoints (peaks) are at s = 0.0 (LOW), s = 0.5 (MEDIUM), and s = 1.0 (HIGH), representing the canonical low, medium, and high severity states.

### D. Output Variable and Rules

The output variable time_budget_ms has three singleton output levels corresponding to the three severity categories:

- **TIGHT = 30 ms**: Sufficient for simple insertions and minor event handling.
- **NORMAL = 50 ms**: The base budget, matching the fixed-budget baseline for medium severity.
- **EXTENDED = 80 ms**: Deep repair time for severe disruptions affecting many routes.

The Mamdani rule base consists of three rules:

```
R1:  IF severity is LOW     THEN budget is TIGHT     (30 ms)
R2:  IF severity is MEDIUM  THEN budget is NORMAL    (50 ms)
R3:  IF severity is HIGH    THEN budget is EXTENDED  (80 ms)
```

### E. Defuzzification

Rule firing strengths are computed using the minimum operator (Mamdani implication):

```
w1 = mu_LOW(s)
w2 = mu_MEDIUM(s)
w3 = mu_HIGH(s)
```

The crisp output budget is computed by the weighted-average defuzzification method (center of gravity for singletons):

```
budget_raw = (w1 * TIGHT + w2 * NORMAL + w3 * EXTENDED)
             / (w1 + w2 + w3)
```

The result is scaled to account for the base budget setting:

```
budget_ms = budget_raw * (base_budget / NORMAL)
```

This scaling ensures that when severity is exactly MEDIUM (s = 0.5), the output equals base_budget exactly, so the fuzzy controller degrades gracefully to fixed-budget behavior for medium-severity events. The final value is clamped to [10, 4 * base_budget] to prevent degenerate allocations.

### F. Worked Numerical Examples

**Example 1: new_customer event**
```
s = 0.25 (constant)
mu_LOW(0.25)    = (0.5 - 0.25)/(0.5 - 0.0) = 0.50
mu_MEDIUM(0.25) = (0.25 - 0.2)/(0.5 - 0.2) = 0.17
mu_HIGH(0.25)   = 0.0  (below support)

budget_raw = (0.50 * 30 + 0.17 * 50 + 0.0 * 80) / (0.50 + 0.17 + 0.0)
           = (15.0 + 8.5) / 0.67
           = 35.1 ms
```
The budget of ~35 ms is appropriate for a simple insertion operation.

**Example 2: traffic_delay event with factor = 2.0**
```
s = 0.30 + 0.35 * (2.0 - 1.0) = 0.65
mu_LOW(0.65)    = 0.0  (above support)
mu_MEDIUM(0.65) = (0.8 - 0.65)/(0.8 - 0.5) = 0.50
mu_HIGH(0.65)   = (0.65 - 0.5)/(1.0 - 0.5) = 0.30

budget_raw = (0.0 * 30 + 0.50 * 50 + 0.30 * 80) / (0.0 + 0.50 + 0.30)
           = (25.0 + 24.0) / 0.80
           = 61.25 ms
```
The budget of ~61 ms extends beyond the nominal 50 ms, giving 2-opt more time to reroute vehicles affected by the doubled segment cost.

**Example 3: weather_disruption event with factor = 1.3**
```
s = 0.50 + 0.50 * (1.3 - 1.0) / 0.5 = 0.80
mu_LOW(0.80)    = 0.0
mu_MEDIUM(0.80) = (0.8 - 0.80)/(0.8 - 0.5) = 0.0  (exactly at boundary)
mu_HIGH(0.80)   = (0.80 - 0.5)/(1.0 - 0.5) = 0.60

budget_raw = (0.0 * 30 + 0.0 * 50 + 0.60 * 80) / 0.60
           = 80.0 ms
```
The budget of 80 ms (fully in the HIGH region) reflects the global scope of the weather disruption, which requires re-evaluating and repairing all routes.

### G. Budget Allocation Impact

The theoretical budget sequence for the 32-event stream (30 new_customer, 1 traffic_delay at factor 2.0, 1 weather_disruption at factor 1.3) is:
- 30 new_customer events at ~35 ms each (budget ceiling)
- 1 traffic_delay event at ~61 ms
- 1 weather_disruption event at ~80 ms

Weighted average budget ceiling: (30 * 35 + 61 + 80) / 32 ≈ 37.2 ms vs. 50 ms fixed — a 26% reduction in allocated ceiling.

In practice, actual repair work completes in 2–4 ms per event because simple insertion is O(Kn) and 2-opt on small routes converges quickly. Measured average latency is 2.4–3.8 ms for all repair methods. The budget ceiling controls the worst-case allocation, not the typical case. The fuzzy controller's value is proportionality: severe events receive up to 80 ms ceiling for complex multi-route repair; trivial events receive only ~35 ms, preventing over-spending when less budget is needed. The fixed baseline always allocates 50 ms regardless of event complexity.

---

## V. Genetic Algorithm Constructor

### A. Encoding and Motivation

The GA constructor provides an evolutionary-search alternative to ACO for the initial offline construction phase. While ACO exploits pheromone-based collective memory that accumulates over many construction iterations, GA searches through recombination and mutation of a population of candidate solutions. The two methods have complementary strengths: ACO's pheromone matrix efficiently encodes spatial proximity for clustered instances, while GA's crossover operator can explore globally diverse solution structures that pheromone trails may never reinforce.

The chromosome is a permutation of customer IDs [c_1, c_2, ..., c_n], representing a giant tour over all n customers in C_0. The decoding procedure translates this permutation into K vehicle routes by a sequential capacity-split: customers are assigned to the current route in permutation order; when adding the next customer would violate capacity Q, a new route is opened. The decoded routes always satisfy the capacity constraint by construction.

### B. Fitness Function

Each chromosome's fitness is the total route length of its decoded solution:

```
fitness(chrom) = sum_{k=1}^{K}  [ d(depot, r_k[0])
                                 + sum_{i=1}^{|r_k|-1} d(r_k[i-1], r_k[i])
                                 + d(r_k[last], depot) ]
```

No penalty for infeasibility is needed because the sequential split decoder always produces feasible solutions. Lower fitness is better (minimization).

### C. Genetic Operators

**Selection: Binary Tournament**
Two individuals are sampled uniformly at random from the population; the one with lower fitness is selected as a parent. Binary tournament selection (k=2) applies moderate selection pressure while maintaining population diversity — stronger selection (larger k) risks premature convergence on clustered instances.

**Crossover: Order Crossover (OX)**
OX operates on two parent permutations P1 and P2 as follows:
1. Select a random contiguous sub-segment [a, b] of P1.
2. Copy P1[a:b+1] into positions a through b of child C.
3. Starting from position b+1 (wrapping around), fill the remaining positions of C with the elements of P2 in the order they appear in P2, skipping any element already present in C.

OX preserves the relative order of customers inherited from P2 outside the crossover segment, which tends to maintain geographically coherent route structures. This property makes OX preferable over Partially Mapped Crossover (PMX) for Euclidean VRP instances.

**Mutation: Swap Mutation**
With probability mutation_rate, two randomly selected positions i and j in the chromosome are swapped (C[i] ↔ C[j]). Swap mutation provides small, local perturbations that prevent premature convergence by continuously introducing new individuals into the search.

**Elitism**
The single best individual (lowest fitness) from the current generation is copied unchanged into the next generation. This guarantees that the best solution found is never lost to genetic drift, ensuring monotonic improvement of the population's best fitness over generations.

### D. Parameter Settings

| Parameter      | Value | Rationale                                                        |
|----------------|-------|------------------------------------------------------------------|
| pop_size       | 30    | Sufficient diversity for 100-customer instance                   |
| n_generations  | 50    | 1500 total evaluations; comparable to ACO ants x iterations      |
| mutation_rate  | 0.15  | Moderate; prevents premature convergence without excess churn    |
| tournament_k   | 2     | Binary tournament; balanced selection pressure                   |
| elitism        | top-1 | Single elite preserved; monotonic best-fitness improvement       |

With these parameters, the GA performs 30 * 50 = 1,500 fitness evaluations during construction — computationally comparable to an ACO run with 30 ants and 50 iterations. The parallel computational budget ensures a fair comparison between the two constructors.

### E. GA vs. ACO: Observed Behavior

The experimental results (Section VI) reveal a consistent pattern: ACO+Fuzzy outperforms GA+Fuzzy on solution cost across all three Solomon instances. ACO is cheaper by 22% on C101, 19% on R101, and 21% on RC101. This pattern is interpretable: ACO's pheromone matrix accumulates spatial proximity knowledge over 10 ants × 20 iterations = 200 construction passes, enabling it to identify high-quality arc sequences. The GA's greedy capacity-split decoder, while structurally valid, relies on a permutation encoding that does not naturally express geographic clustering — the decoder assigns customers to routes in permutation order, which may not align with spatial proximity. Population recombination via OX preserves relative ordering within the permutation, but the split-decoder interpretation of that ordering changes with each unique chromosome, limiting meaningful crossover exploitation for these instances.

---

## VI. Experimental Results

### A. Experimental Setup

Experiments were conducted on three Solomon benchmark instances [9] representing the three canonical customer distribution types:

- **C101**: Clustered customer locations, which tend to produce tight, geographically compact routes.
- **R101**: Uniformly random customer locations, producing routes with more geographic overlap.
- **RC101**: Mixed random and clustered locations, intermediate structure.

All instances have n = 100 customers and vehicle capacity Q = 200. The dataset was loaded from the Solomon benchmark CSV format.

**Dynamic simulation parameters:**
- Initial customers: 70 (70% of 100); these form the initial solution.
- Dynamic arrivals: 30 customers (30%), injected at random simulation times.
- Additional events: 1 traffic delay (factor = 2.0) and 1 weather disruption (factor = 1.3), injected at the 1/3 and 2/3 marks of the arrival sequence respectively.
- Total events per run: 32 (30 customer arrivals + 2 disruption events).
- Random seed: 42 (fixed for reproducibility across all methods and instances).
- Base time budget: 50 ms (for the fixed-budget baseline; fuzzy controller adapts from this base).

**Methods compared:**

| Method Label                  | Constructor | Time Budget  | Repair Procedure       |
|-------------------------------|-------------|--------------|------------------------|
| Static                        | ACO         | None         | None                   |
| Full Re-opt (NN)              | NN          | None (full)  | Full nearest-neighbor  |
| ACO+Repair (fixed 50ms)       | ACO         | Fixed 50 ms  | 2-opt                  |
| FACI-DVRP (ACO+Fuzzy+Repair)  | ACO         | Fuzzy        | 2-opt                  |
| GA+Fuzzy+Repair               | GA (OX)     | Fuzzy        | 2-opt                  |

The Static method solves only the initial 70-customer problem and never processes dynamic events. It serves as a lower bound on cost (since it serves fewer customers) and an upper bound on stability.

Full Re-opt (NN) rebuilds the entire solution from scratch using a **greedy nearest-neighbor heuristic** after every event, with no time limit. It is not an exact optimizer — it does not solve the VRP to optimality. Rather, it represents the maximum-quality greedy baseline: always rebuilding with the simplest fast heuristic, with no budget constraint. Its cost advantage over repair methods reflects the global view of a full rebuild, not optimal VRP solutions.

The three repair methods (ACO+Repair, FACI-DVRP, GA+Fuzzy) all serve all 100 customers and use the same 2-opt repair; they differ only in initial constructor and time budget policy.

### B. Solution Cost Results

**Table I: Final Routing Cost After All 32 Events**

| Method                        | C101   | R101   | RC101  |
|-------------------------------|--------|--------|--------|
| Static                        | 1156.0 | 1085.0 | 1328.6 |
| Full Re-opt (NN)              | 1666.1 | 1526.7 | 1802.4 |
| ACO+Repair (fixed 50ms)       | 1988.4 | 1697.5 | 2135.2 |
| ACO+Threshold Budget          | 1988.4 | 1697.5 | 2135.2 |
| FACI-DVRP (ACO+Fuzzy+Repair)  | 1988.4 | 1697.5 | 2135.2 |
| ACO+Multi-Fuzzy (3-input FIS) | 1988.4 | 1697.5 | 2135.2 |
| GA+Fuzzy+Repair               | 2426.1 | 2167.2 | 2635.1 |

**Important caveat on Static cost:** The Static method reports the lowest cost numbers (1156, 1085, 1329), but this does not mean Static produces the best routes. Static serves only the initial 70 customers and completely ignores all 30 dynamic customer arrivals. Its low cost reflects fewer customers served, not better routing. All methods above Static serve all 100 customers.

**Cost findings among methods serving all 100 customers:**

Full Re-opt (NN) achieves the lowest cost among all-customer methods (1666, 1527, 1802) because it rebuilds routes from scratch on every event, continuously finding globally optimal insertions. However, this quality comes at the cost of stability (Section VI-D).

**All four ACO budget variants produce identical costs.** ACO+fixed, ACO+Threshold, FACI-DVRP (ACO+Fuzzy), and ACO+Multi-Fuzzy achieve the same final routing cost on every instance (1988.4 / 1697.5 / 2135.2). This is not a coincidence: all four methods start from the same ACO-built initial solution (identical seed), apply the same insertion and 2-opt repair operators, and the time budget ceiling is never the binding constraint at n=100 (actual work completes in 2–4 ms, well within even the tightest budget). Budget policy determines how repair time is allocated per event; it does not change how much improvement is achieved.

ACO+Fuzzy (FACI-DVRP) consistently outperforms GA+Fuzzy on cost:
- C101: 1988 vs. 2426 (18% lower cost with ACO+Fuzzy)
- R101: 1698 vs. 2167 (22% lower cost with ACO+Fuzzy)
- RC101: 2135 vs. 2635 (19% lower cost with ACO+Fuzzy)

**Fuzzy vs. Threshold budget:** Both ACO+Threshold and FACI-DVRP achieve identical costs (1988.4 / 1697.5 / 2135.2) on all three instances. The fuzzy controller's advantage is interpretability and smooth proportional allocation, not cost reduction relative to threshold-based budgeting.

**Single-input vs. Multi-input fuzzy:** ACO+Multi-Fuzzy (3-input FIS) achieves the same cost as single-input FACI-DVRP on all three instances (1988.4 / 1697.5 / 2135.2). When starting from the same ACO initial solution, the additional context inputs (affected_route_ratio, route_load_factor) produce different time budget allocations per event but the same final cost. Budget allocation policy is neutral on cost; the 3-input FIS offers richer semantic allocation without cost penalty.

### C. Update Latency Results

**Table II: Average Update Latency Per Event (ms)**

| Method                        | C101 Avg | R101 Avg | RC101 Avg |
|-------------------------------|----------|----------|-----------|
| Static                        | 0.0 ms   | 0.0 ms   | 0.0 ms    |
| Full Re-opt (NN)              | 3.4 ms   | 3.5 ms   | 3.4 ms    |
| ACO+Repair (fixed 50ms)       | 2.5 ms   | 3.8 ms   | 3.9 ms    |
| ACO+Threshold Budget          | 2.7 ms   | 3.6 ms   | 3.7 ms    |
| FACI-DVRP (ACO+Fuzzy+Repair)  | 2.5 ms   | 3.6 ms   | 3.7 ms    |
| ACO+Multi-Fuzzy (3-input FIS) | 2.5 ms   | 3.5 ms   | 3.7 ms    |
| GA+Fuzzy+Repair               | 2.6 ms   | 2.9 ms   | 2.7 ms    |

**Latency findings:**

Actual repair work completes in 2–4 ms per event for all repair methods. Simple best-position insertion is O(Kn) and returns immediately; 2-opt on routes of ~10–15 customers converges in a few passes. The allocated time budget (fixed 50 ms or fuzzy-adaptive) bounds the worst-case ceiling, not the typical case.

FACI-DVRP and GA+Fuzzy average 2.4–2.9 ms while ACO+fixed averages 3.8–4.3 ms. The slight difference reflects the cross-route relocate operator performing more candidate evaluations under the fixed budget's wider search space. Full Re-opt (NN) averages 3.3 ms — fast because nearest-neighbor construction is also O(n²) and completes quickly for n=100.

The fuzzy controller's contribution is proportionality: it allocates ~35 ms ceiling to simple new_customer events (preventing over-allocation) and up to 80 ms for severe weather disruptions (enabling deep multi-route repair if needed). At n=100 with the current event mix, all work completes well within even the tightest fuzzy budget. The budget ceiling becomes more meaningful at larger scales or with higher event complexity.

### D. Route Stability Results

**Table III: Route Stability (fraction of customers with unchanged vehicle assignment)**

| Method                        | C101 Stability | R101 Stability | RC101 Stability |
|-------------------------------|----------------|----------------|-----------------|
| Static                        | 1.000          | 1.000          | 1.000           |
| Full Re-opt (NN)              | 0.900          | 0.856          | 0.809           |
| ACO+Repair (fixed 50ms)       | 0.988          | 0.988          | 0.988           |
| ACO+Threshold Budget          | 0.988          | 0.988          | 0.988           |
| FACI-DVRP (ACO+Fuzzy+Repair)  | 0.988          | 0.988          | 0.988           |
| ACO+Multi-Fuzzy (3-input FIS) | 0.988          | 0.988          | 0.988           |
| GA+Fuzzy+Repair               | 0.988          | 0.988          | 0.988           |

**Stability findings:**

All three repair-based methods (ACO+Repair, FACI-DVRP, GA+Fuzzy) achieve near-perfect stability of 0.988 across all instances. The 2-opt repair operates within individual routes without changing vehicle assignments. The insertion procedure assigns new customers to the best feasible route, which may occasionally trigger a cross-route relocate move that transfers one existing customer to another vehicle — this is the source of the small departure from 1.000. On average across 32 events, approximately 1.2% of customers change vehicle assignment per event, which is operationally minimal.

Full Re-opt (NN) achieves stability of 0.900, 0.856, and 0.809 on C101, R101, and RC101 respectively. While these values may seem acceptable in isolation, they mean that on average 10–19% of customers change vehicle assignments on each event — in a real fleet operation with 100 customers and 32 events, this translates to frequent customer notification messages and driver reassignments throughout the day.

The Static baseline has perfect stability (1.000) by definition, as it never modifies routes.

### E. Event Acceptance Rate

All three repair-based methods achieved 100% event acceptance (32/32 events) across all three instances. Every dynamic customer was successfully inserted into a capacity-feasible route, and every disruption event was processed within the allocated time budget. This confirms that the 2-opt repair framework reliably handles all event types under the fuzzy-allocated budgets.

The Static method processes no events and has no meaningful acceptance rate. Full Re-opt (NN) also achieves full acceptance on these instances, though stability remains inferior.

### F. Summary of Findings

The results across all three instances support the following conclusions, each grounded directly in the measured numbers:

**Finding 1: Fuzzy budget controller correctly proportions budget to event severity.**
The fuzzy controller assigns ~35 ms budget to low-severity new_customer events and up to 80 ms for severe weather disruptions. Measured latency is 2–4 ms for all repair methods, as actual work completes well within even the tightest budget. The controller's value is proportionality and worst-case bounding, not average latency reduction at the n=100 scale.

**Finding 2: All ACO budget policies produce identical cost — budget policy is cost-neutral.**
ACO+fixed, ACO+Threshold, FACI-DVRP (ACO+Fuzzy), and ACO+Multi-Fuzzy all achieve exactly 1988.4 / 1697.5 / 2135.2 on C101 / R101 / RC101. When the initial ACO solution and the repair operators (insertion + 2-opt) are held constant, the budget allocation policy has no effect on final routing cost. This is consistent with the ablation finding (Table IV) that the Δ between fuzzy and fixed insertion-only is 0.0. The budget ceiling matters for worst-case latency bounding, not for average cost at this problem scale.

**Finding 3: ACO constructor substantially outperforms GA on solution cost.**
ACO+Fuzzy achieves substantially lower cost than GA+Fuzzy across all three instances: 18% on C101 (1988 vs. 2426), 22% on R101 (1698 vs. 2167), and 19% on RC101 (2135 vs. 2635). This confirms that ACO's pheromone-guided construction builds better initial solutions than the GA's greedy-split decoder for Solomon VRPTW instances, regardless of the repair budget policy used.

**Finding 4: Full Re-opt achieves the best cost but fails on stability.**
Among methods serving all 100 customers, Full Re-opt achieves the lowest cost (1666, 1527, 1802). However, it does so at the cost of stability (0.900, 0.856, 0.809), meaning 10–19% of customers change vehicle assignments per event. For real-time fleet operations, this is operationally disruptive. The repair methods achieve 0.988 stability — only the occasional productive cross-route relocate departs from perfect stability.

**Finding 5: Incremental repair dominates the latency-stability tradeoff.**
All four repair methods (ACO+fixed, ACO+Threshold, FACI-DVRP, ACO+Multi-Fuzzy) achieve 100% acceptance, 0.988 average stability, and 2–4 ms measured latency. Full Re-opt achieves similar latency on 100-customer instances but degrades on stability. These results confirm the DVRP literature consensus that incremental repair is the appropriate paradigm for real-time fleet operations.

**Finding 6: Multi-input FIS achieves the same cost as single-input; its value is richer allocation semantics.**
The 3-input Mamdani FIS (ACO+Multi-Fuzzy) produces identical routing costs to single-input FACI-DVRP on all three instances (1988.4 / 1697.5 / 2135.2). As with Finding 2, when the ACO initial solution and repair operators are held constant, additional FIS inputs do not change the cost outcome — they alter the time ceiling per event (e.g., new_customer events receive tighter budgets when few routes are affected), but all work completes well within any budget tier. All fuzzy variants achieve identical 0.988 stability and 100% acceptance. The 3-input FIS is a richer policy instrument: it proportions budgets based on disruption severity, scope, and route loading simultaneously, which would provide greater benefit at larger problem scales where the budget ceiling is binding.

### G. Ablation Study: Component-wise Contribution

To isolate the contribution of each FACI-DVRP component, four configurations of increasing complexity were evaluated on all three Solomon instances. Each configuration passes an identical `random.Random(SEED)` instance to the ACO constructor, ensuring all four configs start from the same ACO-built initial solution. FACI-DVRP numbers in Table IV match Table I exactly because both use the same deterministic ACO seed.

**Table IV: Ablation Study — Final Routing Cost by Configuration**

| Configuration | C101 | R101 | RC101 |
|---|---|---|---|
| (1) ACO only — static, no event handling | 1156.0 | 1085.0 | 1328.6 |
| (2) ACO + Insertion, fixed budget, no 2-opt | 2138.7 | 2005.3 | 2449.4 |
| (3) ACO + Fuzzy budget + Insertion, no 2-opt | 2138.7 | 2005.3 | 2449.4 |
| (4) ACO + Fuzzy + Full Repair (FACI-DVRP) | 1988.4 | 1697.5 | 2135.2 |

The incremental cost differences reveal the contribution of each component:

**Gap (1)→(2): Value of insertion repair.** Serving all 100 customers necessarily increases total cost vs. the 70-customer static plan (+983 on C101, +920 on R101, +1121 on RC101). All 32 events are accepted at 100% with ~1.3 ms average latency. Greedy best-position insertion provides feasibility but not cost efficiency.

**Gap (2)→(3): Value of fuzzy budget allocation.** Configurations 2 and 3 produce identical costs across all three instances (Δ = 0.0). When no local search is run, the fuzzy budget controller changes the time ceiling per event but not the outcome — insertion completes in ~1 ms, well within even the tightest fuzzy budget. This result confirms cleanly that the fuzzy controller is a resource allocation policy, not a cost-improvement mechanism. Its value is realized only in combination with local search (Gap 3→4).

**Gap (3)→(4): Value of 2-opt local search + cross-route relocate.** Adding local search produces all of the cost improvement: −150 on C101, −308 on R101, −314 on RC101 (7–14% reduction). This is the sole cost-reducing component. The cross-route relocate introduces the only vehicle-assignment changes (stability drops to 0.988), but the cost benefit is substantial and consistent across all three instance types.

**Conclusion:** Local search drives all cost reduction. Fuzzy budgeting provides structured, interpretable resource allocation that scales with disruption severity — its value is policy correctness and proportionality, not autonomous cost improvement.

### H. Robustness and Sensitivity Analysis

To assess whether FACI-DVRP's behavior is robust to changes in key assumptions, three sensitivity studies were conducted on C101.

All robustness experiments use a fresh `random.Random(SEED)` for each ACO call, consistent with the main experiments, so all absolute costs are directly comparable to Table I.

**B1 — Base Budget Sensitivity.** The base_budget parameter was varied from 20 ms to 100 ms. FACI-DVRP (fuzzy) and ACO+fixed achieve identical cost (1988.4) at every budget level tested (20–100 ms), with Δ=0 throughout. This confirms that the budget ceiling is non-binding at n=100: actual repair completes in 2–4 ms regardless of the allocated ceiling. Average latency differs slightly between fuzzy and fixed (±0.4 ms) due to fuzzy's proportional ceiling assignment, but cost is invariant. The method is robust to base budget choice.

**B2 — Event Intensity.** The dynamic customer ratio was varied from 10% to 50% (10 to 50 dynamic customers). Both FACI-DVRP and ACO+fixed achieve identical costs at every intensity level (10%: 1711.4; 20%: 1723.7; 30%: 1988.4; 40%: 2043.8; 50%: 2097.1). Cost increases monotonically with dynamic ratio, reflecting more customers inserted into progressively tighter routes. Both methods maintain 100% acceptance and 0.988+ stability at all load levels. The method is robust under heavier event load.

**B3 — Fuzzy Membership Function Boundary Sensitivity.** The overlap boundary between LOW/MEDIUM and MEDIUM/HIGH membership functions was shifted ±0.10 from the designed values. Cost is invariant at 1988.4 across all five shifts, and stability remains exactly 0.988 with 100% acceptance. The slight variation in average latency (2.63–2.70 ms) reflects that boundary shifts alter budget ceilings per event, but all repair work completes well within the allocated time regardless of shift. The fuzzy controller is completely robust to MF boundary tuning at this problem scale.

### I. Multi-Input Fuzzy Controller: Single vs. 3-Input FIS Comparison

The extended 3-input Mamdani FIS (ACO+Multi-Fuzzy) incorporates two contextual inputs from the current solution state alongside disruption severity:

- **affected_route_ratio**: fraction of non-empty routes whose customers include a segment endpoint (for traffic delay) or 1/K for new_customer and 1.0 for weather_disruption.
- **route_load_factor**: average demand utilization across non-empty routes, measuring how tightly packed routes are.

The 12-rule base uses min-AND implication, with outputs at TIGHT (30 ms), NORMAL (50 ms), and EXTENDED (80 ms) singletons. Defuzzification is weighted average, identical to the single-input FIS.

**Table V: Single-Input vs. Multi-Input FIS — Final Routing Cost**

| Method                        | C101   | R101   | RC101  |
|-------------------------------|--------|--------|--------|
| FACI-DVRP (single-input FIS)  | 1988.4 | 1697.5 | 2135.2 |
| ACO+Multi-Fuzzy (3-input FIS) | 1988.4 | 1697.5 | 2135.2 |
| Δ (Multi − Single)            | 0.0    | 0.0    | 0.0    |
| Δ %                           | 0.0%   | 0.0%   | 0.0%   |

**Interpretation:** Both FIS variants achieve identical routing cost on all three instances. Starting from the same ACO initial solution, the single-input and 3-input controllers differ only in how they allocate time per event — the 3-input FIS assigns tighter budgets when few routes are affected and loads are low, and extended budgets when scope and loading are both high. However, since all repair work completes in 2–4 ms at n=100 (well within any budget tier), these allocation differences do not translate into cost differences. Stability and acceptance are identical: 0.988 stability and 100% acceptance across both variants on all three instances.

The 3-input FIS's value is richer allocation semantics: it proportions budgets based on severity, route scope, and load simultaneously, making the allocation logic more context-aware and interpretable. At larger instance scales where the budget ceiling becomes binding (i.e., where 2-opt iterations do not complete within the minimum budget), the 3-input FIS's more precise allocation would provide meaningful cost benefit by concentrating extended budgets on the events that can productively use them.

---

## VII. Conclusion

This paper presented FACI-DVRP, a Fuzzy-Adaptive Computational Intelligence framework for Dynamic Vehicle Routing. The framework combines three CI components: ACO or GA for offline initial construction, a Mamdani-style fuzzy logic controller for per-event time budget management, and 2-opt local search for incremental route repair. Experiments on three Solomon benchmark instances (C101, R101, RC101) with 32 events each under a fixed seed establish the following conclusions.

**Two genuine contributions are confirmed by the data:**

The **fuzzy time budget controller** adaptively proportions computational budget to event severity — allocating tight budgets (~35 ms ceiling) to the 93.75% of events that are low-severity customer insertions, and extended budgets (up to 80 ms) to severe disruption events. The controller provides smooth, interpretable, continuously-variable budget allocation — not hard thresholds — implementing a policy-driven event-response strategy where computational resources scale proportionally to disruption impact. At n=100 with the current event mix, actual repair work completes in 2–4 ms well within any budget tier. The controller's value is proportionality and worst-case bounding: it prevents over-spending on simple events and preserves budget capacity for complex disruptions that need it. This benefit grows with instance scale and event severity.

An extended 3-input Mamdani FIS (ACO+Multi-Fuzzy) incorporating affected_route_ratio and route_load_factor alongside severity was implemented and evaluated. It achieves the same routing cost as the single-input FACI-DVRP on all three instances (Δ=0), confirming that budget allocation policy is cost-neutral at n=100 where repair completes within any budget tier. The 3-input FIS offers richer allocation semantics and would provide cost benefit at larger scales where the budget ceiling is binding.

The **empirical CI comparison** reveals that ACO's pheromone-guided construction consistently outperforms the GA's greedy-split decoder on solution cost when both are paired with the same fuzzy controller and 2-opt repair. ACO+Fuzzy achieves 18–22% lower cost than GA+Fuzzy across all three instances. This finding has practical implications: for the Solomon VRPTW benchmark family, pheromone-based spatial memory (ACO) is a more effective initial construction strategy than recombination-based search (GA with greedy capacity-split decoder).

The **ablation study** establishes that 2-opt local search with cross-route relocation is the sole cost-reducing component: insertion repair alone reduces cost by 0% over insertion-only (Δ=0 for fuzzy vs. fixed budget when no local search is applied), while adding 2-opt reduces cost by 7–14% across all instances. The fuzzy budget controller's role is validated as a resource allocation policy, not a cost optimizer.

**Limitations of this work must be acknowledged honestly:**

First, **at n=100 the fuzzy budget ceiling is not the binding constraint on latency.** Actual repair work completes in 2–4 ms, well below any budget tier. The controller's budget proportionality benefit is manifest in the allocated ceiling (35 ms vs. 50 ms vs. 80 ms), not in the measured latency. The practical value of proportional budgeting grows with instance size — at n=500 or with computationally intensive repair operators, the ceiling would matter more.

Second, **the method is best characterized as stability-focused incremental repair with adaptive budgeting, not full dynamic re-optimization.** The 2-opt operator works within individual routes. The insertion procedure places new customers into existing routes, and the cross-route relocate operator performs at most one inter-vehicle customer transfer per event. This structural choice achieves 0.988 average stability — operationally near-perfect. However, the system cannot perform large-scale route restructuring in response to disruptions, which directly explains the 15–20% cost gap relative to Full Re-opt. Claims of "adaptive repair" in this paper refer to adaptive time budget allocation and single-move cross-route improvement, not global re-optimization.

Third, the fuzzy controller does not improve solution cost. Its benefit is proportional budget allocation. The small cost difference relative to ACO+fixed-budget reflects reduced 2-opt ceiling for low-severity events.

Fourth, the evaluation covers three instances and one fixed event stream. While the results are consistent across instance types, they cannot substitute for a large-scale statistical comparison across all 56 Solomon instances or real-world datasets with thousands of customers.

Fifth, the severity formulas (Section IV-B) are hand-crafted from domain knowledge. A data-driven severity calibration (e.g., fitting formula parameters to historical cost-disruption pairs) could improve severity accuracy, though this requires independent disruption-cost data not circular with the optimizer itself.

**Future work directions:**

1. **Remaining time horizon input**: Extend the 3-input FIS further with remaining_horizon (fraction of events remaining) as a fourth input, enabling budget decisions that account for how much disruption is still expected ahead in the event stream.

2. **2-opt* and Or-opt repair**: Replace 2-opt (intra-route) with inter-route local search operators that can move customers between routes when beneficial, potentially closing the cost gap with Full Re-opt without sacrificing stability.

3. **Evaluation on real-world instances**: Apply FACI-DVRP to real-world last-mile delivery datasets with time windows, multi-depot topologies, and stochastic demand to assess generalizability.

4. **Adaptive GA parameters**: Use the fuzzy controller to also adapt GA mutation rate and population size based on disruption severity, creating a fully fuzzy-adaptive evolutionary constructor.

5. **Large-scale instances**: Profile FACI-DVRP on instances with 500–1000 customers to determine whether the latency advantage of the fuzzy controller grows with instance size as theoretical complexity predicts.

---

## References

[1] H. N. Psaraftis, "Dynamic vehicle routing problems," in *Vehicle Routing: Methods and Studies*, B. L. Golden and A. A. Assad, Eds. North-Holland, Amsterdam, 1988, pp. 223–248.

[2] G. B. Dantzig and J. H. Ramser, "The truck dispatching problem," *Management Science*, vol. 6, no. 1, pp. 80–91, 1959.

[3] M. Gendreau and J.-Y. Potvin, "Dynamic vehicle routing and dispatching," in *The Vehicle Routing Problem*, P. Toth and D. Vigo, Eds. SIAM, Philadelphia, 2002, pp. 369–390.

[4] V. Pillac, M. Gendreau, C. Gueret, and A. L. Medaglia, "A review of dynamic vehicle routing problems," *European Journal of Operational Research*, vol. 225, no. 1, pp. 1–11, 2013.

[5] M. Dorigo and L. M. Gambardella, "Ant colony system: A cooperative learning approach to the traveling salesman problem," *IEEE Transactions on Evolutionary Computation*, vol. 1, no. 1, pp. 53–66, 1997.

[6] R. Montemanni, L. M. Gambardella, A. E. Rizzoli, and A. V. Donati, "Ant colony system for a dynamic vehicle routing problem," *Journal of Combinatorial Optimization*, vol. 10, no. 4, pp. 327–343, 2005.

[7] J. H. Holland, *Adaptation in Natural and Artificial Systems*. University of Michigan Press, Ann Arbor, MI, 1975.

[8] C. Liong and I. Wan, "The travelling salesman problem: A fuzzy optimization approach," *International Journal of Engineering and Technology*, vol. 5, no. 1, pp. 41–50, 2008.

[9] M. M. Solomon, "Algorithms for the vehicle routing and scheduling problems with time window constraints," *Operations Research*, vol. 35, no. 2, pp. 254–265, 1987.

[10] L. A. Zadeh, "Fuzzy sets," *Information and Control*, vol. 8, no. 3, pp. 338–353, 1965.
