#!/usr/bin/env python3
"""Capture the nightly Metabase order count shown on the LaborClock analytics endpoint.

This is intentionally simple: at 10 PM it records whatever the backend's
`orders` action is showing for that operating day, so the next morning CPO can
use the saved same-day order number instead of querying current-day orders.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxqVHIs-EuELAmjMNV3nmFf1z2kPSU2OcRzczOGGtZQSEAsel53IKO5FFw1_odyc6G7BA/exec"
ROOT = Path(__file__).resolve().parent
ARCHIVE_ROOT = ROOT / "standup_archive"
SNAPSHOT_ROOT = ROOT / "labor_intelligence" / "order_snapshots"


def today_local() -> str:
    return dt.datetime.now().date().isoformat()


def fetch_orders(facility: str = "") -> dict:
    params = {"action": "orders"}
    if facility:
        params["facility"] = facility
    url = SCRIPT_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def snapshot_orders(date: str, facility: str = "") -> dict:
    payload = fetch_orders(facility=facility)
    snapshot = {
        "ok": bool(payload.get("ok", True)),
        "date": date,
        "capturedAt": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "LaborClock analytics Metabase orders action at scheduled 10 PM snapshot",
        "facility": facility or payload.get("facility") or "all",
        "ordersToday": int(float(payload.get("ordersToday") or 0)),
        "byFacility": payload.get("byFacility") or {},
        "lastSync": payload.get("lastSync"),
        "raw": payload,
    }
    if not snapshot["ordersToday"] and not snapshot["byFacility"]:
        raise RuntimeError(f"orders snapshot returned no order counts: {payload}")
    return snapshot


def write_snapshot(snapshot: dict) -> list[Path]:
    date = snapshot["date"]
    archive_dir = ARCHIVE_ROOT / date
    archive_dir.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)

    paths = [
        archive_dir / f"metabase_order_snapshot_{date}.json",
        SNAPSHOT_ROOT / f"metabase_order_snapshot_{date}.json",
    ]
    text = json.dumps(snapshot, indent=2, sort_keys=True)
    for path in paths:
        path.write_text(text)

    index_path = SNAPSHOT_ROOT / "orders_by_date.json"
    try:
        index = json.loads(index_path.read_text()) if index_path.exists() else {}
    except Exception:
        index = {}
    index[date] = {
        "date": date,
        "total": snapshot["ordersToday"],
        "byFacility": snapshot.get("byFacility") or {},
        "capturedAt": snapshot.get("capturedAt"),
        "lastSync": snapshot.get("lastSync"),
        "sourceFile": str(paths[0]),
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True))
    paths.append(index_path)
    return paths


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=today_local(), help="Operating date to attach to this snapshot. Defaults to local today.")
    parser.add_argument("--facility", default="", help="Optional facility filter if the backend supports it.")
    parser.add_argument("--print", action="store_true", help="Print a short success summary. Cron runs silent on success by default.")
    parser.add_argument("--allow-past-date", action="store_true", help="Dangerous manual override: allow saving the current live orders endpoint under a past date.")
    args = parser.parse_args(argv)

    today = today_local()
    if args.date != today and not args.allow_past_date:
        raise SystemExit(
            f"Refusing to save current live orders under non-current date {args.date}. "
            f"Run this snapshot on the operating date itself, or pass --allow-past-date only if you are intentionally backfilling from a verified source."
        )

    snapshot = snapshot_orders(args.date, facility=args.facility)
    paths = write_snapshot(snapshot)
    if args.print:
        print(
            f"Captured Metabase order snapshot for {args.date}: "
            f"{snapshot['ordersToday']} orders | byFacility={snapshot.get('byFacility') or {}} | "
            f"saved {paths[0]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
