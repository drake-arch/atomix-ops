#!/usr/bin/env python3
"""Publish Drake's dated EOD custom-question markdown into the EOD intake HTML.

Input markdown format:
  # Atomix EOD Questions — YYYY-MM-DD
  ## Kody
  1. Question text
  ## Hugh
  - OFF Thursday and Friday — skip EOD questions.

This updates the DAILY_CUSTOM_QUESTION_SETS block in atomix-eod-main/atomix-eod-main/index.html.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_HTML = ROOT / "atomix-eod-main" / "atomix-eod-main" / "index.html"
NAME_ORDER = ["Kody", "Luis", "Emyly", "Hugh", "Adam", "Norman", "Burke"]
ALIASES = {"Emily": "Emyly", "Louise": "Luis", "Cody": "Kody"}


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_questions(markdown: str) -> dict[str, list[str]]:
    sections = re.split(r"(?m)^##\s+", markdown)
    result: dict[str, list[str]] = {}
    for sec in sections[1:]:
        lines = sec.splitlines()
        if not lines:
            continue
        name = ALIASES.get(lines[0].strip(), lines[0].strip())
        body = "\n".join(lines[1:]).strip()
        questions: list[str] = []
        for line in body.splitlines():
            raw = line.strip()
            if not raw:
                continue
            m = re.match(r"^\d+[.)]\s*(.+)$", raw)
            if m:
                questions.append(m.group(1).strip())
            elif raw.startswith("-") and re.search(r"\b(off|sick|excused|skip)\b", raw, re.I):
                questions.append(re.sub(r"^[-\s]+", "", raw).strip())
        if name:
            result[name] = questions
    return result


def build_block(qs: dict[str, list[str]]) -> str:
    lines = ["    const DAILY_CUSTOM_QUESTION_SETS = {"]
    first_person = True
    for name in NAME_ORDER:
        questions = qs.get(name, [])
        if not questions:
            continue
        if not first_person:
            lines[-1] += ","
        first_person = False
        lines.append(f"      {js_string('Today Custom EOD — ' + name)}: [")
        for i, q in enumerate(questions, 1):
            required = "false" if re.search(r"\b(off|sick|excused|skip|no eod required)\b", q, re.I) else "true"
            key = "excused_note" if required == "false" and i == 1 else f"custom_q{i}"
            comma = "," if i < len(questions) else ""
            lines.append(f"        {{ key: '{key}', label: {js_string(q)}, type: 'textarea', required: {required} }}{comma}")
        lines.append("      ]")
    lines.append("    };")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("questions_md", type=Path)
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    args = ap.parse_args()

    qs = parse_questions(args.questions_md.read_text())
    if not qs:
        raise SystemExit(f"No questions parsed from {args.questions_md}")
    block = build_block(qs)
    html = args.html.read_text()
    pattern = re.compile(r"    const DAILY_CUSTOM_QUESTION_SETS = \{.*?\n    \};", re.S)
    new_html, count = pattern.subn(block, html, count=1)
    if count != 1:
        raise SystemExit(f"Could not replace DAILY_CUSTOM_QUESTION_SETS in {args.html}")
    args.html.write_text(new_html)
    print(f"Updated {args.html} from {args.questions_md}")
    for name in NAME_ORDER:
        if name in qs:
            print(f"- {name}: {len(qs[name])} question(s)")


if __name__ == "__main__":
    main()
