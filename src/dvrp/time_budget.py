import time
from typing import Callable, TypeVar

T = TypeVar("T")


def run_with_time_budget(
    budget_ms: int,
    step_fn: Callable[[], T],
    accept_fn: Callable[[T], bool] | None = None,
) -> T | None:
    """
    Runs step_fn repeatedly until time budget is exhausted.
    Optionally filters step results via accept_fn.
    Returns the last accepted result (or last result if accept_fn is None).
    Guarantees at least one execution of step_fn.
    """
    deadline = time.perf_counter() + (budget_ms / 1000.0)
    best: T | None = None

    while True:
        result = step_fn()
        
        if accept_fn is None or accept_fn(result):
            best = result
        
        if time.perf_counter() >= deadline:
            break

    return best
