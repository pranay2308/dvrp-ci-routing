"""
src/dvrp/fuzzy_budget.py

Fuzzy Logic Adaptive Time Budget Controller for DVRP.

This module implements a Mamdani-style fuzzy inference system (FIS) that
dynamically adjusts the repair time budget per event based on disruption
severity. This is the third CI technique in the FACI-DVRP framework,
alongside ACO (initial construction) and 2-opt local search (route repair).

Fuzzy System Design
-------------------
Input  : disruption_severity  (float in [0, 1])
Output : time_budget_ms       (float in [20, 100])

Membership Functions (triangular):
  Severity:  LOW    -> trimf(0.0, 0.0, 0.4)
             MEDIUM -> trimf(0.2, 0.5, 0.8)
             HIGH   -> trimf(0.6, 1.0, 1.0)

  Budget:    TIGHT    -> 30 ms  (crisp centroid)
             NORMAL   -> 50 ms
             EXTENDED -> 80 ms

Fuzzy Rules:
  R1: IF severity is LOW    THEN budget is TIGHT
  R2: IF severity is MEDIUM THEN budget is NORMAL
  R3: IF severity is HIGH   THEN budget is EXTENDED

Defuzzification: weighted average of crisp output centroids.

Severity Mapping (per event type):
  new_customer      -> 0.25  (low disruption, simple insertion)
  traffic_delay     -> 0.3 + 0.35 * (factor - 1.0)  (scales with delay)
  weather_disruption-> 0.5 + 0.5 * min((factor - 1.0) / 0.5, 1.0)
"""

from typing import Tuple


# ---------------------------------------------------------------------------
# Membership functions
# ---------------------------------------------------------------------------

def _trimf(x: float, a: float, b: float, c: float) -> float:
    """Triangular membership function on [a, b, c].

    Returns 0 strictly outside (a, c); at the peak b returns 1.
    Endpoints a and c are included in support so that degenerate
    functions where a==b or b==c (used for LOW and HIGH) return 1
    at the peak.
    """
    if x < a or x > c:
        return 0.0
    if x <= b:
        return (x - a) / (b - a) if b > a else 1.0
    return (c - x) / (c - b) if c > b else 1.0


# Severity membership functions
def _sev_low(s: float) -> float:
    return _trimf(s, 0.0, 0.0, 0.5)


def _sev_medium(s: float) -> float:
    return _trimf(s, 0.2, 0.5, 0.8)


def _sev_high(s: float) -> float:
    return _trimf(s, 0.5, 1.0, 1.0)


# ---------------------------------------------------------------------------
# Crisp output centroids (ms)
# ---------------------------------------------------------------------------

BUDGET_TIGHT    = 30.0
BUDGET_NORMAL   = 50.0
BUDGET_EXTENDED = 80.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def event_severity(event: dict) -> float:
    """
    Map a DVRP event dict to a normalized severity score in [0, 1].

    new_customer      : 0.25 (low — simple best-position insertion)
    traffic_delay     : 0.30 + 0.35 * (factor - 1.0)  [clamped to 1.0]
    weather_disruption: 0.50 + 0.50 * (factor - 1.0) / 0.5  [clamped to 1.0]
    """
    etype = event.get("type", "")
    if etype == "new_customer":
        return 0.25
    elif etype == "traffic_delay":
        factor = event.get("factor", 1.0)
        return min(0.30 + 0.35 * (factor - 1.0), 1.0)
    elif etype == "weather_disruption":
        factor = event.get("factor", 1.0)
        return min(0.50 + 0.50 * (factor - 1.0) / 0.5, 1.0)
    return 0.25


def fuzzy_time_budget(event: dict, base_budget_ms: int = 50) -> int:
    """
    Compute an adaptive time budget (ms) for a DVRP event using fuzzy logic.

    The result is a weighted average of crisp centroids, scaled so that
    the NORMAL rule exactly matches base_budget_ms.

    Parameters
    ----------
    event          : DVRP event dict with keys 'type' and optionally 'factor'
    base_budget_ms : baseline budget (ms); used to scale the fuzzy output

    Returns
    -------
    Adaptive time budget in milliseconds (integer).
    """
    sev = event_severity(event)

    # Fire each rule (min operator for implication)
    w_tight    = _sev_low(sev)
    w_normal   = _sev_medium(sev)
    w_extended = _sev_high(sev)

    total_weight = w_tight + w_normal + w_extended
    if total_weight < 1e-9:
        return base_budget_ms

    # Defuzzify: weighted average of crisp centroids
    raw = (
        w_tight    * BUDGET_TIGHT +
        w_normal   * BUDGET_NORMAL +
        w_extended * BUDGET_EXTENDED
    ) / total_weight

    # Scale so NORMAL -> base_budget_ms
    scale = base_budget_ms / BUDGET_NORMAL
    budget = int(round(raw * scale))

    # Clamp to [10, base_budget_ms * 4]
    return max(10, min(budget, base_budget_ms * 4))


def threshold_time_budget(event: dict, base_budget_ms: int = 50) -> int:
    """
    Simple severity-threshold budget controller (baseline for comparison).

    Uses hard-coded thresholds instead of fuzzy smooth interpolation:
      severity < 0.4  ->  TIGHT  (30 ms scaled)
      severity >= 0.4 ->  EXTENDED (80 ms scaled)

    This is the 'naive adaptive' alternative to fuzzy logic.
    Comparing fuzzy vs. threshold shows the value of smooth interpolation.
    """
    sev = event_severity(event)
    scale = base_budget_ms / BUDGET_NORMAL
    if sev < 0.4:
        return int(round(BUDGET_TIGHT * scale))
    else:
        return int(round(BUDGET_EXTENDED * scale))


# ---------------------------------------------------------------------------
# Multi-input Fuzzy Controller
# ---------------------------------------------------------------------------
#
# Extends the single-input FIS with two contextual inputs:
#
#   Input 1 — disruption_severity s ∈ [0, 1]  (same as before)
#   Input 2 — affected_route_ratio a ∈ [0, 1]
#             Fraction of non-empty routes affected by the event.
#             new_customer: 1/K (inserting into exactly one route)
#             traffic_delay: routes containing segment endpoints / total routes
#             weather_disruption: 1.0 (all routes affected)
#   Input 3 — route_load_factor l ∈ [0, 1]
#             Average demand utilisation across non-empty routes.
#             High load → harder to relocate customers → more repair budget needed.
#
# Membership functions:
#   severity:      LOW trimf(0,0,0.5)  MED trimf(0.2,0.5,0.8)  HIGH trimf(0.5,1,1)
#   affected_ratio: FEW trimf(0,0,0.5)  MANY trimf(0.5,1,1)
#   load_factor:   LIGHT trimf(0,0,0.6)  HEAVY trimf(0.4,1,1)
#
# Rule base (12 rules, min-AND Mamdani, output singletons TIGHT/NORMAL/EXTENDED):
#   sev=LOW,  aff=FEW,  load=LIGHT → TIGHT
#   sev=LOW,  aff=FEW,  load=HEAVY → TIGHT
#   sev=LOW,  aff=MANY, load=LIGHT → NORMAL
#   sev=LOW,  aff=MANY, load=HEAVY → NORMAL
#   sev=MED,  aff=FEW,  load=LIGHT → TIGHT
#   sev=MED,  aff=FEW,  load=HEAVY → NORMAL
#   sev=MED,  aff=MANY, load=LIGHT → NORMAL
#   sev=MED,  aff=MANY, load=HEAVY → EXTENDED
#   sev=HIGH, aff=FEW,  load=LIGHT → NORMAL
#   sev=HIGH, aff=FEW,  load=HEAVY → EXTENDED
#   sev=HIGH, aff=MANY, load=LIGHT → EXTENDED
#   sev=HIGH, aff=MANY, load=HEAVY → EXTENDED
#
# Defuzzification: weighted average of singletons (same as single-input FIS).


def _aff_few(a: float) -> float:
    return _trimf(a, 0.0, 0.0, 0.5)


def _aff_many(a: float) -> float:
    return _trimf(a, 0.5, 1.0, 1.0)


def _load_light(l: float) -> float:
    return _trimf(l, 0.0, 0.0, 0.6)


def _load_heavy(l: float) -> float:
    return _trimf(l, 0.4, 1.0, 1.0)


# Rule table: (sev_mf, aff_mf, load_mf, output_singleton)
_MULTI_RULES = [
    ("low",  "few",  "light", BUDGET_TIGHT),
    ("low",  "few",  "heavy", BUDGET_TIGHT),
    ("low",  "many", "light", BUDGET_NORMAL),
    ("low",  "many", "heavy", BUDGET_NORMAL),
    ("med",  "few",  "light", BUDGET_TIGHT),
    ("med",  "few",  "heavy", BUDGET_NORMAL),
    ("med",  "many", "light", BUDGET_NORMAL),
    ("med",  "many", "heavy", BUDGET_EXTENDED),
    ("high", "few",  "light", BUDGET_NORMAL),
    ("high", "few",  "heavy", BUDGET_EXTENDED),
    ("high", "many", "light", BUDGET_EXTENDED),
    ("high", "many", "heavy", BUDGET_EXTENDED),
]


def compute_context_inputs(event: dict, solution) -> tuple[float, float]:
    """
    Compute the two contextual inputs for the multi-input FIS from
    the current event and solution state.

    Returns
    -------
    affected_ratio : float in [0, 1]
    load_factor    : float in [0, 1]
    """
    non_empty = [r for r in solution.routes if r.customers]
    K = max(len(non_empty), 1)

    # --- affected_route_ratio ---
    etype = event.get("type", "")
    if etype == "new_customer":
        affected_ratio = 1.0 / K          # insertion touches exactly one route
    elif etype == "traffic_delay":
        id_a, id_b = event.get("segment", (None, None))
        affected = sum(
            1 for r in non_empty
            if any(c.id == id_a or c.id == id_b for c in r.customers)
        )
        affected_ratio = affected / K
    else:  # weather_disruption
        affected_ratio = 1.0

    # --- route_load_factor ---
    if not non_empty:
        load_factor = 0.0
    else:
        utilizations = [
            sum(c.demand for c in r.customers) / r.vehicle.capacity
            for r in non_empty
        ]
        load_factor = min(sum(utilizations) / len(utilizations), 1.0)

    return affected_ratio, load_factor


def multi_fuzzy_time_budget(
    event: dict,
    solution,
    base_budget_ms: int = 50,
) -> int:
    """
    Multi-input Mamdani fuzzy controller for DVRP repair budget allocation.

    Uses three inputs:
      - disruption_severity   (from event type/factor)
      - affected_route_ratio  (from current solution state)
      - route_load_factor     (from current solution state)

    12-rule base with min-AND implication and weighted-average defuzzification.

    Parameters
    ----------
    event          : DVRP event dict
    solution       : current Solution object (to compute contextual inputs)
    base_budget_ms : baseline budget for scaling

    Returns
    -------
    Adaptive time budget in milliseconds (integer).
    """
    sev = event_severity(event)
    affected_ratio, load_factor = compute_context_inputs(event, solution)

    # Membership values for each input
    mu_sev  = {"low": _sev_low(sev),    "med": _sev_medium(sev), "high": _sev_high(sev)}
    mu_aff  = {"few": _aff_few(affected_ratio), "many": _aff_many(affected_ratio)}
    mu_load = {"light": _load_light(load_factor), "heavy": _load_heavy(load_factor)}

    # Fire all 12 rules (min-AND)
    numerator = 0.0
    denominator = 0.0
    for sev_label, aff_label, load_label, output in _MULTI_RULES:
        strength = min(mu_sev[sev_label], mu_aff[aff_label], mu_load[load_label])
        numerator   += strength * output
        denominator += strength

    if denominator < 1e-9:
        return base_budget_ms

    raw = numerator / denominator
    scale = base_budget_ms / BUDGET_NORMAL
    budget = int(round(raw * scale))
    return max(10, min(budget, base_budget_ms * 4))


def explain_multi_budget(event: dict, solution, base_budget_ms: int = 50) -> str:
    """Human-readable explanation of the multi-input fuzzy budget decision."""
    sev = event_severity(event)
    affected_ratio, load_factor = compute_context_inputs(event, solution)
    budget = multi_fuzzy_time_budget(event, solution, base_budget_ms)
    return (
        f"event={event.get('type')}  "
        f"sev={sev:.2f}  aff={affected_ratio:.2f}  load={load_factor:.2f}  "
        f"-> budget={budget}ms"
    )


def explain_budget(event: dict, base_budget_ms: int = 50) -> str:
    """
    Return a human-readable explanation of the fuzzy budget decision.
    Useful for paper figures and debugging.
    """
    sev = event_severity(event)
    budget = fuzzy_time_budget(event, base_budget_ms)
    w_tight    = _sev_low(sev)
    w_normal   = _sev_medium(sev)
    w_extended = _sev_high(sev)
    return (
        f"event={event.get('type')} severity={sev:.2f} | "
        f"mu_low={w_tight:.2f} mu_med={w_normal:.2f} mu_high={w_extended:.2f} "
        f"-> budget={budget}ms"
    )
