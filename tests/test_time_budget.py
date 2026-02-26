import time
from dvrp.time_budget import run_with_time_budget


def test_time_budget_basic_behavior():
    """Test that time budget runs multiple steps and respects deadline."""
    calls = {"n": 0}

    def step():
        calls["n"] += 1
        time.sleep(0.005)  # 5ms per step
        return calls["n"]

    start = time.perf_counter()
    best = run_with_time_budget(budget_ms=50, step_fn=step)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # Should run at least once
    assert best is not None
    assert calls["n"] >= 1
    
    # Should respect deadline reasonably (allow some overhead)
    assert elapsed_ms < 150