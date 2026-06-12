#!/usr/bin/env python3
"""Atomix EOD / Good Morning audit gate.

Fails closed before a standup or Good Morning email is sent when the source date,
questions, comics, or deck data look wrong.

Key comms rule:
- Weekends produce no new Atomix EOD email/deck.
- Monday morning reviews Friday EOD.
- Tuesday-Friday review the previous business/calendar day.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/home/fabric041/work/atomix-ops')
SHEET_ID = '130wcBqy6QUzPM9KID9fXAHUP47a8NGVPSxVOaPt3qo0'
GIDS = {'Reports': '146026037', 'Answers': '489860443'}
SCRIPT_RE = re.compile(r"<script id=['\"]deck-data['\"] type=['\"]application/json['\"]>(.*?)</script>", re.S)
CRITICAL_PEOPLE = ['kody', 'kayla', 'hunter']  # Ops, CX, Finance question persistence smoke checks


def expected_source_date(today: dt.date | None = None) -> dt.date:
    today = today or dt.datetime.now(ZoneInfo('America/Chicago')).date()
    if today.weekday() == 0:  # Monday -> Friday
        return today - dt.timedelta(days=3)
    if today.weekday() == 6:  # Sunday manual run -> Friday
        return today - dt.timedelta(days=2)
    if today.weekday() == 5:  # Saturday manual run -> Friday
        return today - dt.timedelta(days=1)
    return today - dt.timedelta(days=1)


def fetch_sheet(gid: str) -> list[dict[str, str]]:
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}'
    data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read().decode('utf-8-sig', 'replace')
    return list(csv.DictReader(io.StringIO(data)))


def load_deck(path: Path) -> dict:
    html = path.read_text(errors='ignore')
    match = SCRIPT_RE.search(html)
    if not match:
        raise ValueError(f'deck-data script missing: {path}')
    return json.loads(match.group(1))


def latest_deck_for(source: str) -> Path | None:
    archive = ROOT / 'standup_archive' / source
    candidates = []
    if archive.exists():
        candidates.extend(archive.glob(f'*source_{source}*.html'))
        candidates.extend(archive.glob(f'CLICK_TO_OPEN*{source}*.html'))
    candidates.extend(ROOT.glob(f'cleo-standup-meeting-{source}.html'))
    candidates.extend(ROOT.glob(f'cleo-standup-deck-{source}.html'))
    files = [p for p in candidates if p.is_file()]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def run_comic_gate(deck_path: Path) -> tuple[bool, str]:
    gate = ROOT / 'standup_comic_gate.py'
    if not gate.exists():
        return False, 'standup_comic_gate.py missing'
    proc = subprocess.run([sys.executable, str(gate), str(deck_path)], cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    return proc.returncode == 0, proc.stdout.strip()


def audit(source: str, deck_path: Path | None, strict_comics: bool = True) -> tuple[int, dict]:
    failures: list[str] = []
    warnings: list[str] = []

    # Weekend guard is informational for manual runs; cron schedule prevents weekends.
    today = dt.datetime.now(ZoneInfo('America/Chicago')).date()
    if today.weekday() >= 5:
        warnings.append('Weekend manual run detected. Scheduled Atomix comms are weekday-only; do not send unless explicitly approved.')

    # Source date must be the expected operating day unless explicitly overridden.
    expected = expected_source_date(today).isoformat()
    if source != expected:
        warnings.append(f'Source date {source} does not match expected operating day {expected}. If this was not explicit, stop.')

    reports = fetch_sheet(GIDS['Reports'])
    answers = fetch_sheet(GIDS['Answers'])
    source_reports = [r for r in reports if r.get('date') == source]
    source_answers = [a for a in answers if a.get('date') == source]
    if not source_reports:
        failures.append(f'No EOD reports found for source date {source}.')
    if not source_answers:
        failures.append(f'No EOD answers found for source date {source}.')

    # Question persistence smoke check against local ShiftFlow question definitions when present.
    shiftflow = ROOT / 'shiftflow.html'
    if shiftflow.exists():
        text = shiftflow.read_text(errors='ignore').lower()
        for pid in CRITICAL_PEOPLE:
            if pid not in text:
                failures.append(f'Question persistence smoke check failed: {pid} not found in shiftflow.html.')
    else:
        failures.append('shiftflow.html missing; cannot verify EOD question surface exists.')

    if deck_path is None:
        deck_path = latest_deck_for(source)
    if not deck_path or not deck_path.exists():
        failures.append(f'No standup deck found for source date {source}.')
        deck_data = None
    else:
        try:
            deck_data = load_deck(deck_path)
            deck_date = str(deck_data.get('date', ''))
            if deck_date != source:
                failures.append(f'Deck source date mismatch: deck has {deck_date}, expected {source}.')
            slides = deck_data.get('slides', [])
            if not slides:
                failures.append('Deck has no slides.')
            person_slides = [s for s in slides if s.get('type') == 'person']
            if not person_slides:
                failures.append('Deck has no person slides.')
            submitted = [s for s in person_slides if s.get('submitted')]
            if source_reports and not submitted:
                failures.append('Sheet has reports, but deck has no submitted person slides.')
            missing_comic = [s.get('title') or s.get('pid') for s in submitted if not (s.get('comic') or s.get('comic_pages'))]
            if missing_comic:
                failures.append('Submitted people missing comic data: ' + ', '.join(map(str, missing_comic)))
        except Exception as exc:  # noqa: BLE001
            deck_data = None
            failures.append(f'Cannot parse deck data: {exc}')

        if strict_comics:
            ok, output = run_comic_gate(deck_path)
            if not ok:
                failures.append('Comic gate failed. Do not send until fixed.\n' + output)

    result = {
        'ok': not failures,
        'source_date': source,
        'expected_source_date': expected,
        'deck_path': str(deck_path) if deck_path else '',
        'reports_found': len(source_reports),
        'answers_found': len(source_answers),
        'failures': failures,
        'warnings': warnings,
    }
    return (0 if not failures else 1), result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-date', default=expected_source_date().isoformat(), help='EOD source date YYYY-MM-DD. Defaults to prior Atomix business day; Monday = Friday.')
    ap.add_argument('--deck', type=Path, default=None, help='Optional standup deck HTML to audit.')
    ap.add_argument('--no-strict-comics', action='store_true', help='Skip raster comic gate. Do not use before sending.')
    args = ap.parse_args()
    code, result = audit(args.source_date, args.deck, strict_comics=not args.no_strict_comics)
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
