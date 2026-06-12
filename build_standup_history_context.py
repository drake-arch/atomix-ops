#!/usr/bin/env python3
"""Build a compact historical context file from past Atomix EOD/standup artifacts.

Sources inspected:
- standup_archive/**/eod_questions_*.md
- standup_archive/**/*.html with embedded deck-data JSON
- Google Sheet Answers export when reachable

Output is intentionally compact so the current deck builder can read prior patterns,
recurring questions, repeated blockers, and comic/deck lessons before building today.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import html
import io
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "standup_archive"
OUTDIR = ROOT / "standup_history"
SID = "130wcBqy6QUzPM9KID9fXAHUP47a8NGVPSxVOaPt3qo0"
ANSWERS_GID = "489860443"
PEOPLE = ["kody", "luis", "emyly", "hugh", "adam", "norman", "burke"]
SCRIPT_RE = re.compile(r"<script id=['\"]deck-data['\"] type=['\"]application/json['\"]>(.*?)</script>", re.S)


def clean(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def parse_question_md(path: Path) -> dict:
    text = path.read_text(errors="ignore")
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    date = m.group(1) if m else "unknown"
    people: dict[str, list[str]] = {}
    for sec in re.split(r"(?m)^##\s+", text)[1:]:
        lines = sec.splitlines()
        if not lines:
            continue
        name = clean(lines[0])
        qs = []
        for line in lines[1:]:
            raw = line.strip()
            if not raw:
                continue
            mm = re.match(r"^\d+[.)]\s*(.+)$", raw)
            if mm:
                qs.append(clean(mm.group(1)))
            elif raw.startswith("-"):
                qs.append(clean(raw.lstrip("- ")))
        people[name] = qs
    return {"date": date, "path": str(path), "people": people}


def parse_deck(path: Path) -> dict | None:
    text = path.read_text(errors="ignore")
    m = SCRIPT_RE.search(text)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except Exception:
        return None
    people = {}
    for slide in data.get("slides", []):
        if slide.get("type") == "person":
            pid = slide.get("pid") or clean(slide.get("title")).lower()
            people[pid] = {
                "title": slide.get("title"),
                "submitted": bool(slide.get("submitted")),
                "excused": bool(slide.get("excused")),
                "answers": [
                    {"q": clean(a.get("q")), "a": clean(a.get("a")), "kind": a.get("kind", "")}
                    for a in slide.get("answers", [])
                ],
                "comic_page_count": slide.get("comic_page_count"),
                "complexity": slide.get("complexity"),
            }
    return {"date": data.get("date") or "unknown", "path": str(path), "people": people}


def fetch_sheet_answers() -> list[dict]:
    url = f"https://docs.google.com/spreadsheets/d/{SID}/export?format=csv&gid={ANSWERS_GID}"
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8-sig", "replace")
    except Exception as exc:
        return [{"error": f"Sheet fetch failed: {exc}"}]
    return list(csv.DictReader(io.StringIO(raw)))


def summarize(rows: list[dict], question_files: list[dict], decks: list[dict], days: int) -> str:
    cutoff = dt.date.today() - dt.timedelta(days=days)
    by_person = collections.defaultdict(list)
    for r in rows:
        if "error" in r:
            continue
        date = clean(r.get("date"))
        try:
            if dt.date.fromisoformat(date) < cutoff:
                continue
        except Exception:
            pass
        pid = clean(r.get("person_id")).lower()
        if pid in PEOPLE:
            by_person[pid].append({"date": date, "q": clean(r.get("question_text")), "a": clean(r.get("answer"))})

    lines = []
    lines.append(f"# Atomix Standup Historical Context — generated {dt.datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("Purpose: read before building the current EOD/standup deck so today is grounded in prior questions, answers, repeats, and comic/deck context.")
    lines.append("")
    lines.append("## Source coverage")
    lines.append(f"- Question files inspected: {len(question_files)}")
    lines.append(f"- Deck HTML files with deck-data inspected: {len(decks)}")
    lines.append(f"- Sheet answer rows inspected: {0 if rows and 'error' in rows[0] else len(rows)}")
    if rows and "error" in rows[0]:
        lines.append(f"- Sheet warning: {rows[0]['error']}")
    lines.append("")

    lines.append("## Prior custom question files")
    for qf in sorted(question_files, key=lambda x: x["date"])[-10:]:
        lines.append(f"### {qf['date']} — `{qf['path']}`")
        for person, qs in qf["people"].items():
            lines.append(f"- {person}: {len(qs)} question(s)")
            for q in qs[:8]:
                lines.append(f"  - {q}")
    lines.append("")

    lines.append("## Recent submitted answers by person")
    for pid in PEOPLE:
        rows_for = by_person.get(pid, [])[-20:]
        lines.append(f"### {pid.title()}")
        if not rows_for:
            lines.append("- No recent Sheet answers found.")
            continue
        for r in rows_for:
            q = r["q"][:120]
            a = r["a"][:260]
            lines.append(f"- {r['date']} — Q: {q} / A: {a}")
    lines.append("")

    lines.append("## Prior deck/comic context")
    for deck in sorted(decks, key=lambda x: x["date"])[-8:]:
        lines.append(f"### {deck['date']} — `{deck['path']}`")
        for pid, p in deck["people"].items():
            lines.append(f"- {pid}: submitted={p['submitted']} excused={p['excused']} answers={len(p['answers'])} comic_pages={p.get('comic_page_count')} complexity={p.get('complexity')}")
    lines.append("")

    lines.append("## Build reminders")
    lines.append("- Compare today's custom question file against submitted answer question text before building.")
    lines.append("- Same miss as prior day = accountability; different miss = process/audit/system.")
    lines.append("- Comics must be real generated production comic art, not SVG/card/icon fallbacks.")
    lines.append("- Complex EODs can use multiple comic pages/slides inside the same person section.")
    lines.append("- Do not invent missing answers; mark mismatch/missing plainly.")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--out", type=Path, default=OUTDIR / "standup_historical_context_latest.md")
    args = ap.parse_args()

    qfiles = [parse_question_md(p) for p in sorted(ARCHIVE.glob("**/eod_questions_*.md"))]
    decks = [d for d in (parse_deck(p) for p in sorted(ARCHIVE.glob("**/*.html"))) if d]
    rows = fetch_sheet_answers()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    content = summarize(rows, qfiles, decks, args.days)
    args.out.write_text(content)
    dated = args.out.parent / f"standup_historical_context_{dt.date.today().isoformat()}.md"
    dated.write_text(content)
    print(json.dumps({"out": str(args.out), "dated": str(dated), "question_files": len(qfiles), "decks": len(decks), "sheet_rows": 0 if rows and 'error' in rows[0] else len(rows)}, indent=2))


if __name__ == "__main__":
    main()
