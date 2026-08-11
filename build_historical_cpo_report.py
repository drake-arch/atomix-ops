#!/usr/bin/env python3
"""Build the Atomix four-week historical labor CPO dataset and report."""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MONEY_RE = re.compile(r"[^0-9.-]+")
HOURS_RE = re.compile(r"[^0-9.-]+")


def number(value: str, pattern: re.Pattern[str]) -> float:
    cleaned = pattern.sub("", str(value or ""))
    return float(cleaned) if cleaned not in {"", "-", "."} else 0.0


def parse_homebase(path: Path) -> dict:
    facility, start, _, end = path.stem.split("_", 3)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    section = None
    weekly_cost = weekly_hours = None
    daily_costs = {}
    daily_hours = {}
    department_costs = {}
    headers = rows[0][1:]
    for row in rows[1:]:
        label = (row[0] if row else "").strip()
        if label == "Costs":
            section = "costs"
            continue
        if label == "Hours":
            section = "hours"
            continue
        if label == "GRAND TOTAL":
            value = row[1] if len(row) > 1 else ""
            if section == "costs":
                weekly_cost = number(value, MONEY_RE)
            elif section == "hours":
                weekly_hours = number(value, HOURS_RE)
            continue
        if label == "TOTALS":
            target = daily_costs if section == "costs" else daily_hours
            for header, value in zip(headers, row[1:]):
                target[header] = number(value, MONEY_RE if section == "costs" else HOURS_RE)
            continue
        if section == "costs" and label:
            normalized = label.strip()
            department_costs[normalized] = department_costs.get(normalized, 0.0) + sum(
                number(value, MONEY_RE) for value in row[1:]
            )
    if weekly_cost is None or weekly_hours is None:
        raise ValueError(f"Missing GRAND TOTAL cost/hours in {path}")
    return {
        "facility": facility,
        "week_start": start,
        "week_end": end,
        "labor_cost": round(weekly_cost, 2),
        "labor_hours": round(weekly_hours, 2),
        "daily_costs": daily_costs,
        "daily_hours": daily_hours,
        "department_costs": {key: round(value, 2) for key, value in sorted(department_costs.items())},
        "labor_source_file": path.name,
    }


def build(labor_dir: Path, orders_json: Path) -> dict:
    order_payload = json.loads(orders_json.read_text())
    orders = {
        (row["facility"], row["week_start"], row["week_end"]): int(row["orders_shipped"])
        for row in order_payload["weekly_rows"]
    }
    rows = []
    for path in sorted(labor_dir.glob("*.csv")):
        row = parse_homebase(path)
        key = (row["facility"], row["week_start"], row["week_end"])
        if key not in orders:
            raise ValueError(f"No shipped-order result for {key}")
        row["orders_shipped"] = orders[key]
        row["cost_per_order"] = round(row["labor_cost"] / row["orders_shipped"], 4)
        row["orders_per_labor_hour"] = round(row["orders_shipped"] / row["labor_hours"], 2)
        rows.append(row)
    if len(rows) != 8:
        raise ValueError(f"Expected 8 site-weeks, found {len(rows)}")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": "Atomix Historical Weekly Labor CPO",
        "formula": "Homebase labor cost / OMS orders shipped in the same facility week",
        "labor_scope": "All standard operating roles in each Homebase Labor by Role export; salaried employees were excluded at export. Homebase does not provide a billable flag in this report.",
        "week_rules": {"MKE": "Sunday-Saturday", "SLC": "Monday-Sunday"},
        "sources": {
            "labor": "Homebase Labor by Role CSV exports",
            "orders": order_payload.get("source"),
            "orders_sql": order_payload.get("sql"),
            "orders_generated_at": order_payload.get("generated_at"),
        },
        "rows": rows,
    }


def write_csv(payload: dict, path: Path) -> None:
    fields = ["facility", "week_start", "week_end", "labor_hours", "labor_cost", "orders_shipped", "orders_per_labor_hour", "cost_per_order"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in payload["rows"])


def write_html(payload: dict, path: Path) -> None:
    rows = sorted(payload["rows"], key=lambda row: (row["week_start"], row["facility"]))
    table = "".join(
        "<tr>"
        f"<td><strong>{html.escape(row['facility'])}</strong></td>"
        f"<td>{html.escape(row['week_start'])} – {html.escape(row['week_end'])}</td>"
        f"<td>{row['labor_hours']:,.2f}</td>"
        f"<td>${row['labor_cost']:,.2f}</td>"
        f"<td>{row['orders_shipped']:,}</td>"
        f"<td>{row['orders_per_labor_hour']:,.2f}</td>"
        f"<td><strong>${row['cost_per_order']:,.2f}</strong></td>"
        "</tr>" for row in rows
    )
    combined_cost = sum(row["labor_cost"] for row in rows)
    combined_orders = sum(row["orders_shipped"] for row in rows)
    combined_cpo = combined_cost / combined_orders
    path.write_text(f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(payload['title'])}</title>
<style>body{{font:14px system-ui;margin:40px;color:#1f2522}}h1{{color:#063d39}}.cards{{display:flex;gap:16px;margin:24px 0}}.card{{padding:16px 20px;border:1px solid #ccc;border-radius:12px;min-width:180px}}.v{{font-size:26px;font-weight:700;color:#006b52}}table{{border-collapse:collapse;width:100%}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:right}}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}th{{background:#063d39;color:white}}.note{{margin-top:24px;padding:16px;background:#f4f1e8;border-radius:10px;line-height:1.5}}</style></head><body>
<h1>{html.escape(payload['title'])}</h1><p>Four completed operating weeks through August 9, 2026.</p>
<div class="cards"><div class="card"><div>Combined labor</div><div class="v">${combined_cost:,.2f}</div></div><div class="card"><div>Orders shipped</div><div class="v">{combined_orders:,}</div></div><div class="card"><div>Weighted CPO</div><div class="v">${combined_cpo:,.2f}</div></div></div>
<table><thead><tr><th>Site</th><th>Operating week</th><th>Labor hours</th><th>Labor cost</th><th>Orders shipped</th><th>Orders/labor hr</th><th>CPO</th></tr></thead><tbody>{table}</tbody></table>
<div class="note"><strong>Formula:</strong> {html.escape(payload['formula'])}<br><strong>Scope:</strong> {html.escape(payload['labor_scope'])}<br><strong>Week rules:</strong> MKE Sunday–Saturday; SLC Monday–Sunday.<br><strong>Order source:</strong> read-only Metabase SQL over OMS <code>Orders</code>, exact <code>orderStatus='shipped'</code>, excluding deleted and archived orders.</div>
</body></html>""", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labor-dir", type=Path, required=True)
    parser.add_argument("--orders-json", type=Path, required=True)
    parser.add_argument("--data-json", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.labor_dir, args.orders_json)
    args.data_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    args.data_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_csv(payload, args.report_dir / "atomix_historical_weekly_cpo.csv")
    write_html(payload, args.report_dir / "atomix_historical_weekly_cpo.html")
    print(json.dumps([{key: row[key] for key in ("facility", "week_start", "week_end", "labor_cost", "orders_shipped", "cost_per_order")} for row in payload["rows"]], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
