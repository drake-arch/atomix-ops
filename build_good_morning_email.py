#!/usr/bin/env python3
"""Build Drake's 8 AM Atomix Good Morning email.

Purpose:
- Report yesterday's CPO and where labor was spent.
- Compare yesterday against available historicals.
- Include three daily Cleo operating moves from nightly research/cache.
- Produce a professional inline HTML email, no attachments.

Read-only against source systems. Writes local artifacts only.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import json
import math
import random
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/home/fabric041/work/atomix-ops')
LABOR_ROOT = ROOT / 'labor_intelligence'
RESEARCH_ROOT = ROOT / 'labor_intelligence' / 'nightly_research'
REPORT_ROOT = ROOT / 'good_morning_reports'
HOURLY_RATE = 18.50
CPO_TARGET = 4.00
STANDARD_OPS_DEPTS = {'AM Shift','PM Shift','Inbound','Outbound','Inventory','Returns','Facilities','B2B','Kitting'}
NON_CPO_DEPTS = {'Special Projects','MOVE','Backroom Move','Lunch','Break','Unassigned'}
SAYINGS = [
    "Grab some coffee. Let's get the floor cleaner than yesterday.",
    "Coffee up. Clean labor, clean promises, clean closeout.",
    "Start sharp. Today's margin is built one clean handoff at a time.",
    "Let's make the work visible before it becomes expensive.",
    "Small misses get big when nobody owns them. Let's own the day early.",
]
FALLBACK_ACTIONS = [
    {
        'title': 'Tie labor to output by 10 AM',
        'why': 'CPO only improves when supervisors can see hours against shipped orders while the day is still movable.',
        'today': 'Have each facility call out its biggest labor bucket, order count, and whether staffing is ahead/behind demand.'
    },
    {
        'title': 'Name one owner for every blocker',
        'why': 'A blocker without an owner becomes back-office drag and repeat client trust risk.',
        'today': 'For each EOD fire/blocker, record owner, next action, and closeout proof before noon.'
    },
    {
        'title': 'Protect inventory discipline while pushing outbound',
        'why': 'Fast outbound still loses margin if FEFO/lot/LPN discipline is bypassed.',
        'today': 'Spot-check one high-volume pick path and one expiry/lot client for scan discipline and exceptions.'
    },
]


def esc(x) -> str:
    return html.escape(str(x if x is not None else ''))


def money(x) -> str:
    try:
        v = float(x)
        if not math.isfinite(v):
            return '—'
        return f"${v:,.2f}"
    except Exception:
        return '—'


def one(x, suffix='') -> str:
    try:
        v = float(x)
        if not math.isfinite(v):
            return '—'
        return f"{v:,.1f}{suffix}"
    except Exception:
        return '—'


def default_source_date(today: dt.date | None = None) -> str:
    today = today or dt.datetime.now(ZoneInfo('America/New_York')).date()
    # Monday morning should review Friday. Other days review yesterday.
    return (today - dt.timedelta(days=3 if today.weekday() == 0 else 1)).isoformat()


def ensure_labor_report(source_date: str, refresh: bool = False) -> Path:
    path = LABOR_ROOT / source_date / f'labor_intelligence_{source_date}.json'
    if refresh or not path.exists():
        subprocess.run(['python3', 'build_labor_intelligence_report.py', '--date', source_date], cwd=ROOT, check=True, timeout=180)
    return path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def ops_hours(dept_totals: dict) -> float:
    return sum(float(v or 0) for k, v in dept_totals.items() if k in STANDARD_OPS_DEPTS)


def excluded_hours(dept_totals: dict) -> float:
    return sum(float(v or 0) for k, v in dept_totals.items() if k not in STANDARD_OPS_DEPTS)


def calc_metrics(report: dict) -> dict:
    dept_totals = report.get('deptTotals') or {}
    orders = int(float((report.get('snapshot') or {}).get('ordersSnapshot') or 0))
    oh = ops_hours(dept_totals)
    eh = excluded_hours(dept_totals)
    cost = oh * HOURLY_RATE
    cpo = cost / orders if orders else None
    total_h = sum(float(v or 0) for v in dept_totals.values())
    return {
        'date': report.get('date'),
        'orders': orders,
        'ops_hours': oh,
        'excluded_hours': eh,
        'total_hours': total_h,
        'ops_cost': cost,
        'cpo': cpo,
        'dept_totals': dept_totals,
        'order_snapshot_source': (report.get('snapshot') or {}).get('ordersSnapshotSource'),
        'events': (report.get('snapshot') or {}).get('eventsPulled'),
        'people': (report.get('snapshot') or {}).get('peopleInReport'),
        'pack_rate_oph': (report.get('snapshot') or {}).get('packRateAvgOPH'),
        'pack_rate_orders': (report.get('snapshot') or {}).get('packRateTotalOrders'),
        'quality_notes': collect_quality_notes(report),
    }


def collect_quality_notes(report: dict) -> list[str]:
    notes = []
    snap = report.get('snapshot') or {}
    if not snap.get('ordersSnapshot'):
        notes.append('Missing 10 PM order snapshot, so CPO is blocked for this date.')
    if str(snap.get('ordersSnapshotSource') or '').startswith('missing'):
        notes.append('Order source is missing; use the nightly Metabase snapshot as the workaround.')
    flags = 0
    for rec in (report.get('people') or {}).values():
        flags += len(rec.get('flags') or [])
    if flags:
        notes.append(f'{flags} LaborClock timeline cleanup flags found; totals are management intelligence, not payroll truth.')
    return notes[:4]


def load_historicals(source_date: str) -> list[dict]:
    rows = []
    for p in sorted(LABOR_ROOT.glob('*/labor_intelligence_*.json')):
        try:
            data = load_json(p)
            m = calc_metrics(data)
            if m['date'] <= source_date and m['orders']:
                rows.append(m)
        except Exception:
            continue
    rows = sorted(rows, key=lambda x: x['date'])[-7:]
    return rows


def load_actions() -> list[dict]:
    latest = RESEARCH_ROOT / 'latest_recommendations.json'
    if latest.exists():
        try:
            data = load_json(latest)
            actions = data.get('actions') or data.get('recommendations') or []
            clean = []
            for a in actions[:3]:
                if isinstance(a, str):
                    clean.append({'title': a, 'why': '', 'today': ''})
                elif isinstance(a, dict):
                    clean.append({
                        'title': a.get('title') or a.get('action') or 'Operating improvement',
                        'why': a.get('why') or a.get('reason') or '',
                        'today': a.get('today') or a.get('next_step') or a.get('step') or '',
                    })
            if len(clean) == 3:
                return clean
        except Exception:
            pass
    return FALLBACK_ACTIONS


def historical_summary(rows: list[dict], current: dict) -> dict:
    vals = [r['cpo'] for r in rows if r.get('cpo') is not None]
    avg = sum(vals) / len(vals) if vals else None
    best = min(vals) if vals else None
    worst = max(vals) if vals else None
    delta = (current['cpo'] - avg) if current.get('cpo') is not None and avg is not None else None
    return {'avg': avg, 'best': best, 'worst': worst, 'delta': delta, 'count': len(vals)}


def build_plain(current: dict, hist: dict, actions: list[dict]) -> str:
    cpo_text = money(current.get('cpo')) if current.get('cpo') is not None else 'BLOCKED'
    lines = [
        'Good morning Drake and team.',
        random.choice(SAYINGS),
        '',
        "Here are the three things I've learned that can most help us today:",
    ]
    for i, a in enumerate(actions, 1):
        lines.append(f"{i}. {a['title']} — {a.get('today') or a.get('why')}")
    lines += [
        '',
        f"Yesterday labor read ({current['date']}):",
        f"- CPO: {cpo_text} against target {money(CPO_TARGET)}",
        f"- Orders: {current['orders']:,}",
        f"- CPO labor: {one(current['ops_hours'], 'h')} / {money(current['ops_cost'])}",
        f"- Other/project/uncoded labor: {one(current['excluded_hours'], 'h')}",
        f"- Historical avg from available reports: {money(hist.get('avg')) if hist.get('avg') is not None else 'N/A'}",
        '',
        'Where labor was spent:',
    ]
    for dept, hrs in list(current['dept_totals'].items())[:10]:
        lines.append(f"- {dept}: {one(hrs, 'h')}")
    if current.get('quality_notes'):
        lines += ['', 'Data notes:'] + [f"- {n}" for n in current['quality_notes']]
    lines += ['', 'From Cleo', 'Atomix operating nervous system']
    return '\n'.join(lines) + '\n'


def pct_bar(value: float, total: float) -> str:
    pct = 0 if not total else max(0, min(100, value / total * 100))
    return f"<div style='height:8px;background:#e6eee9;border-radius:99px;overflow:hidden;'><div style='width:{pct:.1f}%;height:8px;background:#0b7a5f;border-radius:99px;'></div></div>"


def build_html(current: dict, rows: list[dict], hist: dict, actions: list[dict], source_date: str) -> str:
    saying = random.choice(SAYINGS)
    cpo = current.get('cpo')
    cpo_status = 'Blocked' if cpo is None else ('On track' if cpo <= CPO_TARGET else 'Watch')
    cpo_color = '#7a4b00' if cpo is None else ('#087a5a' if cpo <= CPO_TARGET else '#b42318')
    avg = hist.get('avg')
    if cpo is None:
        read = 'CPO is blocked because the saved order snapshot is missing.'
    elif avg is None:
        read = 'CPO is calculated, but there is not enough historical data for a trend yet.'
    elif cpo <= avg:
        read = f"Yesterday beat the available historical average by {money(avg - cpo)} per order."
    else:
        read = f"Yesterday ran {money(cpo - avg)} per order above the available historical average."

    total_hours = current['total_hours'] or 1
    dept_rows = ''.join(
        f"<tr><td style='padding:10px 0;border-bottom:1px solid #edf2ef;'><b>{esc(dept)}</b><div style='margin-top:6px'>{pct_bar(float(hrs), total_hours)}</div></td><td style='padding:10px 0;border-bottom:1px solid #edf2ef;text-align:right;font-weight:800;color:#073f38;'>{one(hrs,'h')}</td></tr>"
        for dept, hrs in list(current['dept_totals'].items())[:12]
    )
    hist_rows = ''.join(
        f"<tr><td style='padding:9px 0;border-bottom:1px solid #edf2ef;'>{esc(r['date'])}</td><td style='padding:9px 0;border-bottom:1px solid #edf2ef;text-align:right;'>{r['orders']:,}</td><td style='padding:9px 0;border-bottom:1px solid #edf2ef;text-align:right;'>{one(r['ops_hours'],'h')}</td><td style='padding:9px 0;border-bottom:1px solid #edf2ef;text-align:right;font-weight:800;'>{money(r['cpo'])}</td></tr>"
        for r in rows
    ) or "<tr><td>No historical reports yet.</td></tr>"
    action_cards = ''.join(
        f"<div style='border:1px solid #dfe8e3;border-radius:18px;padding:16px;background:#fbfdfb;margin-bottom:10px;'><div style='font-size:12px;color:#0b7a5f;font-weight:900;letter-spacing:.4px;'>Move {i}</div><h2 style='margin:5px 0 6px;font-size:18px;line-height:1.2;color:#062f35;'>{esc(a['title'])}</h2><p style='margin:0 0 8px;color:#43534d;line-height:1.45;'>{esc(a.get('why'))}</p><p style='margin:0;color:#121615;line-height:1.45;'><b>Today:</b> {esc(a.get('today'))}</p></div>"
        for i, a in enumerate(actions, 1)
    )
    notes = ''.join(f"<li>{esc(n)}</li>" for n in current.get('quality_notes') or []) or '<li>No blocking data notes found in the generated report.</li>'
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#eef4ef;color:#121615;font-family:Arial,Helvetica,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;">Yesterday CPO, labor spend, historical trend, and Cleo's three operating moves for today.</div>
  <div style="max-width:880px;margin:0 auto;padding:26px;">
    <section style="background:#062f35;color:#ffffff;border-radius:28px;padding:30px 30px 26px;margin-bottom:16px;">
      <div style="font-size:13px;letter-spacing:.5px;color:#a3f5c4;font-weight:900;">Atomix Good Morning</div>
      <h1 style="font-size:36px;line-height:1.05;margin:8px 0 10px;letter-spacing:-0.8px;">Good morning Drake and team.</h1>
      <p style="font-size:17px;line-height:1.45;margin:0;color:#e9fff2;">{esc(saying)}</p>
      <p style="font-size:14px;line-height:1.45;margin:18px 0 0;color:#b8d8ca;">Source date: <b>{esc(source_date)}</b>. This email is built from LaborClock, Analytics/Metabase order snapshots, pack-rate snapshots when available, and Cleo's nightly improvement research cache.</p>
    </section>

    <section style="background:#ffffff;border:1px solid #dfe8e3;border-radius:24px;padding:24px;margin-bottom:16px;">
      <div style="font-size:12px;letter-spacing:1.8px;text-transform:uppercase;color:#0b7a5f;font-weight:900;">Here are the three things I've learned that can most help us today</div>
      <div style="margin-top:14px;">{action_cards}</div>
    </section>

    <section style="background:#ffffff;border:1px solid #dfe8e3;border-radius:24px;padding:24px;margin-bottom:16px;">
      <div style="font-size:12px;letter-spacing:1.8px;text-transform:uppercase;color:#0b7a5f;font-weight:900;">Yesterday's labor / CPO read</div>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:14px;"><tr>
        <td style="padding:14px;background:#f4f8f5;border-radius:16px;text-align:center;"><div style="font-size:12px;color:#596b64;text-transform:uppercase;letter-spacing:1px;">CPO</div><div style="font-size:30px;font-weight:900;color:{cpo_color};">{money(cpo) if cpo is not None else 'Blocked'}</div><div style="font-size:12px;color:#596b64;">target {money(CPO_TARGET)}</div></td>
        <td style="padding:14px;background:#f4f8f5;border-radius:16px;text-align:center;"><div style="font-size:12px;color:#596b64;text-transform:uppercase;letter-spacing:1px;">Orders</div><div style="font-size:30px;font-weight:900;color:#062f35;">{current['orders']:,}</div><div style="font-size:12px;color:#596b64;">10 PM snapshot</div></td>
        <td style="padding:14px;background:#f4f8f5;border-radius:16px;text-align:center;"><div style="font-size:12px;color:#596b64;text-transform:uppercase;letter-spacing:1px;">CPO labor</div><div style="font-size:30px;font-weight:900;color:#062f35;">{one(current['ops_hours'],'h')}</div><div style="font-size:12px;color:#596b64;">{money(current['ops_cost'])}</div></td>
        <td style="padding:14px;background:#f4f8f5;border-radius:16px;text-align:center;"><div style="font-size:12px;color:#596b64;text-transform:uppercase;letter-spacing:1px;">Other labor</div><div style="font-size:30px;font-weight:900;color:#062f35;">{one(current['excluded_hours'],'h')}</div><div style="font-size:12px;color:#596b64;">project / uncoded / breaks</div></td>
      </tr></table>
      <p style="font-size:15px;line-height:1.5;color:#26352f;margin:16px 0 0;"><b>Status: {esc(cpo_status)}.</b> {esc(read)}</p>
    </section>

    <section style="background:#ffffff;border:1px solid #dfe8e3;border-radius:24px;padding:24px;margin-bottom:16px;">
      <div style="font-size:12px;letter-spacing:1.8px;text-transform:uppercase;color:#0b7a5f;font-weight:900;">Where yesterday's labor was spent</div>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:10px;">{dept_rows}</table>
    </section>

    <section style="background:#ffffff;border:1px solid #dfe8e3;border-radius:24px;padding:24px;margin-bottom:16px;">
      <div style="font-size:12px;letter-spacing:1.8px;text-transform:uppercase;color:#0b7a5f;font-weight:900;">Historicals / trend</div>
      <p style="font-size:15px;line-height:1.5;color:#26352f;">Available history is short, so this compares one operating day against the current saved daily reports, not a full statistical baseline. Current available average: <b>{money(avg) if avg is not None else 'N/A'}</b>. Best: <b>{money(hist.get('best')) if hist.get('best') is not None else 'N/A'}</b>. Worst: <b>{money(hist.get('worst')) if hist.get('worst') is not None else 'N/A'}</b>.</p>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><th align="left">Date</th><th align="right">Orders</th><th align="right">CPO hrs</th><th align="right">CPO</th></tr>{hist_rows}</table>
    </section>

    <section style="background:#fff8e8;border:1px solid #f1ddb1;border-radius:24px;padding:22px;margin-bottom:16px;">
      <div style="font-size:12px;letter-spacing:1.8px;text-transform:uppercase;color:#7a4b00;font-weight:900;">Data controls / blockers</div>
      <ul style="margin:10px 0 0;padding-left:20px;line-height:1.55;color:#3b3322;">{notes}</ul>
    </section>

    <div style="font-size:13px;color:#53615b;line-height:1.5;padding:4px 2px 20px;">From Cleo<br>Atomix operating nervous system<br>ai.ops@atomixlogistics.com</div>
  </div>
</body></html>"""


def build(source_date: str, outdir: Path, refresh: bool = False) -> dict:
    report_path = ensure_labor_report(source_date, refresh=refresh)
    report = load_json(report_path)
    current = calc_metrics(report)
    rows = load_historicals(source_date)
    hist = historical_summary(rows, current)
    actions = load_actions()
    subject = f"Good Morning — Labor, CPO, and 3 Moves — {source_date}"
    text = build_plain(current, hist, actions)
    html_body = build_html(current, rows, hist, actions, source_date)
    outdir.mkdir(parents=True, exist_ok=True)
    html_path = outdir / 'good_morning_email.html'
    text_path = outdir / 'good_morning_email.txt'
    mml_path = outdir / 'send_good_morning_email.mml'
    summary_path = outdir / 'good_morning_summary.json'
    html_path.write_text(html_body)
    text_path.write_text(text)
    mml_path.write_text(f"From: Cleo <ai.ops@atomixlogistics.com>\nTo: Drake <Drake@atomixlogistics.com>\nSubject: {subject}\n\n<#multipart type=alternative>\n<#part type=text/plain>\n{text}<#part type=text/html>\n{html_body}\n<#/multipart>\n")
    summary = {'subject': subject, 'source_date': source_date, 'html': str(html_path), 'text': str(text_path), 'mml': str(mml_path), 'summary': current, 'historicals': [{'date': r['date'], 'orders': r['orders'], 'ops_hours': r['ops_hours'], 'cpo': r['cpo']} for r in rows], 'hist_summary': hist, 'actions': actions}
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=default_source_date(), help='Operating/source date. Default: prior operating day.')
    ap.add_argument('--outdir', default='', help='Output directory. Default: good_morning_reports/YYYY-MM-DD_8am')
    ap.add_argument('--refresh', action='store_true', help='Re-pull LaborClock report before building email.')
    args = ap.parse_args(argv)
    outdir = Path(args.outdir) if args.outdir else REPORT_ROOT / f'{args.date}_8am'
    summary = build(args.date, outdir, refresh=args.refresh)
    print(json.dumps({'subject': summary['subject'], 'mml': summary['mml'], 'html': summary['html'], 'source_date': summary['source_date'], 'cpo': summary['summary']['cpo'], 'orders': summary['summary']['orders']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
