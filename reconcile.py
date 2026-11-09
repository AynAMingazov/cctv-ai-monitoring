"""Compare visitors counted by the camera with orders registered in the office.

    python reconcile.py --db events.db --orders orders.csv --day 2026-10-15

orders.csv: one row per order with a column `date` (YYYY-MM-DD).
A large gap between visitors and orders is a signal to check the day manually.
"""
from __future__ import annotations

import argparse
import csv

from monitor.events import EventLog


def reconcile(visitors: int, orders: int, tolerance: float = 0.15) -> dict:
    gap = visitors - orders
    flagged = visitors > 0 and gap / visitors > tolerance
    return {"visitors": visitors, "orders": orders, "unregistered": max(gap, 0), "check_needed": flagged}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="events.db")
    ap.add_argument("--orders", required=True)
    ap.add_argument("--day", required=True)
    ap.add_argument("--tolerance", type=float, default=0.15,
                    help="share of visitors allowed without an order (staff, people asking a question)")
    args = ap.parse_args()

    visitors = EventLog(args.db).count("visitor_in", args.day)
    with open(args.orders, encoding="utf-8") as f:
        orders = sum(1 for row in csv.DictReader(f) if row["date"] == args.day)
    print(reconcile(visitors, orders, args.tolerance))


if __name__ == "__main__":
    main()
