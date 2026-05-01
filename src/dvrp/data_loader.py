"""
src/dvrp/data_loader.py

Load Solomon VRPTW benchmark instances from CSV files.

CSV format (from Kaggle dataset):
    CUST NO., XCOORD., YCOORD., DEMAND, READY TIME, DUE DATE, SERVICE TIME
    Row with DEMAND=0 is the depot.

Fleet defaults follow Solomon conventions:
    C1, R1, RC1  ->  25 vehicles, capacity 200
    C2, R2, RC2  ->  3  vehicles, capacity 700
"""

import csv
from pathlib import Path
from typing import List, Tuple

from dvrp.models import Customer, Vehicle


def load_solomon_csv(
    path: str | Path,
) -> Tuple[Customer, List[Customer]]:
    """
    Parse a Solomon CSV file.

    Returns
    -------
    depot     : Customer  (the depot node, demand=0)
    customers : list[Customer]  (all service customers)
    """
    path = Path(path)
    depot = None
    customers: List[Customer] = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cust_no = int(row["CUST NO."])
            x = float(row["XCOORD."])
            y = float(row["YCOORD."])
            demand = float(row["DEMAND"])

            if demand == 0:
                depot = Customer(id=0, x=x, y=y, demand=0)
            else:
                customers.append(Customer(id=cust_no, x=x, y=y, demand=demand))

    if depot is None:
        raise ValueError(f"No depot row (DEMAND=0) found in {path}")

    return depot, customers


def make_fleet(
    instance_path: str | Path,
    override_count: int | None = None,
    override_capacity: float | None = None,
) -> List[Vehicle]:
    """
    Build a vehicle fleet for a Solomon instance.

    Uses Solomon standard defaults unless overrides are supplied:
        C1 / R1 / RC1  ->  25 vehicles, capacity 200
        C2 / R2 / RC2  ->  3  vehicles, capacity 700
    """
    folder = Path(instance_path).parent.name.upper()

    if override_count is not None and override_capacity is not None:
        count, capacity = override_count, override_capacity
    elif folder in ("C2", "R2", "RC2"):
        count, capacity = 3, 700
    else:
        count, capacity = 25, 200

    return [Vehicle(id=i + 1, capacity=capacity) for i in range(count)]
